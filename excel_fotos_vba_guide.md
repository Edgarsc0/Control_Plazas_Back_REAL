# Guía: Generar Excel con Fotografías de Empleados + Macro VBA

> **Propósito:** Replicar en un sistema nuevo la funcionalidad de SIORH que genera un archivo `.xlsm` con fotografías de empleados incrustadas **dentro de la celda**, usando una macro VBA que permite filtrar filas y que las fotos se desplacen junto con ellas.

---

## Índice

1. [Cómo funciona](#1-cómo-funciona)
2. [Dependencias Python](#2-dependencias-python)
3. [Almacenamiento de fotografías](#3-almacenamiento-de-fotografías)
4. [El binario vbaProject.bin](#4-el-binario-vbaprojectbin)
5. [La macro VBA (código fuente)](#5-la-macro-vba-código-fuente)
6. [Código Python del endpoint Django](#6-código-python-del-endpoint-django)
7. [Variante: 10 000 empleados en múltiples hojas](#7-variante-10-000-empleados-en-múltiples-hojas)
8. [URL del endpoint y conexión desde Angular](#8-url-del-endpoint-y-conexión-desde-angular)
9. [Checklist de integración](#9-checklist-de-integración)

---

## 1. Cómo funciona

```
┌─────────────────────────────────────────────────────────────────────┐
│  Django endpoint GET /api/exportar-excel/                           │
│                                                                     │
│  1. Consulta empleados de la BD                                     │
│  2. Lee fotos desde disco (carpeta /fotos/<num_empleado>.jpg)       │
│  3. Crea un Workbook .xlsm con xlsxwriter                           │
│  4. Inyecta vbaProject.bin → habilita macros                        │
│  5. Por cada fila: worksheet.insert_image(..., object_position=1)   │
│     └─ object_position=1 = xlMoveAndSize → foto anclada a la celda │
│  6. Devuelve el archivo como descarga HTTP                          │
└─────────────────────────────────────────────────────────────────────┘
```

**Clave técnica:** `object_position: 1` en xlsxwriter equivale a `Placement = xlMoveAndSize` (valor `1`) en VBA. Esto hace que la imagen se mueva y redimensione junto con su celda — por eso las fotos "siguen" a las filas cuando se filtra.

---

## 2. Dependencias Python

```bash
pip install xlsxwriter Pillow
```

En `requirements.txt`:
```
xlsxwriter>=3.1.0
Pillow>=10.0.0
```

---

## 3. Almacenamiento de fotografías

### Recomendación: carpeta en el filesystem (no BLOB en BD)

```
/ruta/al/back/
└── recursos/
    └── fotos/
        ├── 00012345678.jpg    # nombre = num_empleado (con o sin ceros)
        ├── 00087654321.jpg
        └── ...
```

**Por qué filesystem y no BLOB:**
- Más rápido: lectura paralela con `ThreadPoolExecutor`, caché del SO
- Más fácil de mantener: se pueden agregar/reemplazar fotos sin tocar la BD
- Migración sencilla a S3/MinIO en el futuro

### Función para leer foto desde disco

```python
import os
from pathlib import Path

FOTOS_DIR = Path(__file__).resolve().parent / 'recursos' / 'fotos'

def leer_foto(num_empleado: str) -> bytes | None:
    """Busca la foto por número de empleado en varias variantes de nombre."""
    if not num_empleado:
        return None

    num = str(num_empleado).strip()
    variantes = [
        num,                        # tal cual: 20232019
        num.zfill(11),              # con ceros: 00020232019
        num.lstrip('0') or '0',     # sin ceros: 20232019
    ]

    for nombre in dict.fromkeys(variantes):  # elimina duplicados conservando orden
        for ext in ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'):
            ruta = FOTOS_DIR / f"{nombre}{ext}"
            if ruta.exists():
                try:
                    return ruta.read_bytes()
                except OSError:
                    pass
    return None
```

### Cargar fotos en paralelo (para grandes volúmenes)

```python
from concurrent.futures import ThreadPoolExecutor

def precargar_fotos(lista_num_empleados: list[str], max_workers: int = 8) -> dict[str, bytes]:
    """Devuelve un dict {num_empleado: bytes_foto}. Solo incluye los que tienen foto."""
    def _cargar(num):
        return num, leer_foto(num)

    resultado = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for num, foto in executor.map(_cargar, lista_num_empleados):
            if foto:
                resultado[num] = foto
    return resultado
```

---

## 4. El binario vbaProject.bin

Este archivo es un documento OLE (binario) que contiene el código VBA compilado. **Debe obtenerse una sola vez** y copiarse al proyecto.

### Cómo obtenerlo (una sola vez)

1. Abre Excel → crea un libro nuevo
2. Presiona `Alt + F11` para abrir el editor VBA
3. En el editor, pega el código de la [sección 5](#5-la-macro-vba-código-fuente)
4. Guarda el libro como `.xlsm` (Libro de Excel habilitado para macros)
5. Abre el `.xlsm` como un ZIP (renómbralo a `.zip` temporalmente)
6. Dentro del ZIP, extrae el archivo `xl/vbaProject.bin`
7. Copia ese binario a tu proyecto:

```
tu_back/
└── ws_tuapp/
    └── resources/
        └── vbaProject.bin   ← aquí
```

### Referencia en el código

```python
from pathlib import Path

vba_project_path = Path(__file__).resolve().parent / 'resources' / 'vbaProject.bin'
```

> **Nota:** En SIORH, el binario vive en `ws_siorh/resources/vbaProject.bin`. Puedes **copiar directamente ese mismo archivo** — el VBA que contiene es el mismo que se documenta en la sección 5.

---

## 5. La macro VBA (código fuente)

Este es el código VBA que hace que las imágenes se anclen dentro de las celdas y se desplacen al filtrar.

```vba
Option Explicit

' ─────────────────────────────────────────────────────────────────────────────
' AnclarFotos: Recorre todas las imágenes de la hoja activa y establece
'              Placement = xlMoveAndSize (1), de modo que cada imagen queda
'              anclada a su celda y se desplaza junto con ella al filtrar.
' ─────────────────────────────────────────────────────────────────────────────
Sub AnclarFotos()
    Dim ws As Worksheet
    Dim shp As Shape

    Set ws = ActiveSheet

    For Each shp In ws.Shapes
        If shp.Type = msoPicture Or shp.Type = msoLinkedPicture Then
            shp.Placement = xlMoveAndSize   ' valor = 1
        End If
    Next shp
End Sub

' ─────────────────────────────────────────────────────────────────────────────
' Auto_Open: Se ejecuta automáticamente al abrir el libro.
'            Llama a AnclarFotos para garantizar que las imágenes
'            queden dentro de las celdas desde el primer momento.
' ─────────────────────────────────────────────────────────────────────────────
Sub Auto_Open()
    AnclarFotos
End Sub

' ─────────────────────────────────────────────────────────────────────────────
' Workbook_Open (alternativa en ThisWorkbook): mismo propósito que Auto_Open.
' ─────────────────────────────────────────────────────────────────────────────
' En el módulo ThisWorkbook:
'
' Private Sub Workbook_Open()
'     AnclarFotos
' End Sub
' ─────────────────────────────────────────────────────────────────────────────
```

**Por qué funciona:**
- `xlMoveAndSize` (= 1) le dice a Excel que la imagen debe moverse **y** redimensionarse con la celda.
- Al filtrar filas, Excel mueve las celdas visibles — como la imagen está pegada a su celda, se mueve también.
- `xlsxwriter` establece `object_position: 1` directamente al insertar la imagen, por lo que la macro en realidad es un "seguro" adicional: el posicionamiento correcto ya viene desde Python.

---

## 6. Código Python del endpoint Django

### Vista completa

```python
import os
import tempfile
import datetime
from io import BytesIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PIL import Image as PILImage
import xlsxwriter

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Empleado   # ajusta al modelo de tu sistema


# ── Configuración ──────────────────────────────────────────────────────────
FOTOS_DIR      = Path(__file__).resolve().parent / 'resources' / 'fotos'
VBA_BIN_PATH   = Path(__file__).resolve().parent / 'resources' / 'vbaProject.bin'
MAX_W_PX       = 92    # ancho máximo de la foto en píxeles dentro de la celda
MAX_H_PX       = 74    # alto  máximo
ROW_HEIGHT_PTS = 60    # altura de fila en puntos
FOTOS_WORKERS  = 8     # hilos para lectura paralela de fotos


# ── Helpers ────────────────────────────────────────────────────────────────
def _leer_foto(num_empleado: str) -> bytes | None:
    if not num_empleado:
        return None
    num = str(num_empleado).strip()
    variantes = dict.fromkeys([num, num.zfill(11), num.lstrip('0') or '0'])
    for nombre in variantes:
        for ext in ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'):
            ruta = FOTOS_DIR / f"{nombre}{ext}"
            if ruta.exists():
                try:
                    return ruta.read_bytes()
                except OSError:
                    pass
    return None


def _calcular_escala(raw_bytes: bytes) -> tuple[float, float]:
    """Devuelve (x_scale, y_scale) para que la imagen quepa en MAX_W x MAX_H."""
    try:
        with PILImage.open(BytesIO(raw_bytes)) as img:
            w, h = img.size
        if w > 0 and h > 0:
            ratio = min(MAX_W_PX / w, MAX_H_PX / h, 1.0)
            return ratio, ratio
    except Exception:
        pass
    return 0.5, 0.5


def _insertar_foto(worksheet, row: int, col: int, raw_bytes: bytes) -> None:
    x_scale, y_scale = _calcular_escala(raw_bytes)
    worksheet.insert_image(
        row, col, 'foto.jpg',
        {
            'image_data':      BytesIO(raw_bytes),
            'x_scale':         x_scale,
            'y_scale':         y_scale,
            'x_offset':        3,
            'y_offset':        3,
            'object_position': 1,   # xlMoveAndSize — ancla la imagen a la celda
        },
    )


# ── Endpoint ───────────────────────────────────────────────────────────────
@api_view(['GET'])
def exportar_excel_empleados(request):
    """
    GET /api/exportar-excel-empleados/
    Genera un .xlsm con fotos incrustadas en las celdas.
    Parámetros opcionales (query string):
        search      búsqueda libre
        page        número de página (default 1)
        page_size   registros por hoja (default 1000, máx recomendado)
    """
    params = request.query_params

    # ── 1. Queryset ──────────────────────────────────────────────────────
    queryset = Empleado.objects.all().order_by('num_empleado')

    search = params.get('search', '').strip()
    if search:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(nombre__icontains=search)
            | Q(num_empleado__icontains=search)
            | Q(rfc__icontains=search)
        )

    try:
        page      = max(1, int(params.get('page', 1)))
        page_size = max(1, int(params.get('page_size', 1000)))
    except (ValueError, TypeError):
        page, page_size = 1, 1000

    offset   = (page - 1) * page_size
    page_qs  = queryset[offset: offset + page_size]

    # ── 2. Precargar fotos en paralelo ───────────────────────────────────
    numeros = list(page_qs.values_list('num_empleado', flat=True))

    def _cargar(num):
        return num, _leer_foto(num)

    fotos_map: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=FOTOS_WORKERS) as pool:
        for num, foto in pool.map(_cargar, numeros):
            if foto:
                fotos_map[str(num)] = foto

    # ── 3. Verificar VBA bin ─────────────────────────────────────────────
    if not VBA_BIN_PATH.exists():
        return Response(
            {'detail': f'No se encontró vbaProject.bin en {VBA_BIN_PATH}'},
            status=500,
        )

    # ── 4. Crear Workbook ────────────────────────────────────────────────
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsm')
    os.close(tmp_fd)

    try:
        workbook  = xlsxwriter.Workbook(tmp_path)
        workbook.add_vba_project(str(VBA_BIN_PATH))
        worksheet = workbook.add_worksheet('Empleados')

        # Formatos
        hdr_fmt  = workbook.add_format({
            'bold': True, 'font_color': '#FFFFFF',
            'bg_color': '#265B4E', 'align': 'center',
            'valign': 'vcenter', 'border': 1,
        })
        left_fmt  = workbook.add_format({'align': 'left',   'valign': 'vcenter'})
        right_fmt = workbook.add_format({'align': 'right',  'valign': 'vcenter'})
        ctr_fmt   = workbook.add_format({'align': 'center', 'valign': 'vcenter'})

        # Encabezados y anchos de columna
        COLUMNS = [
            {'header': 'Foto',          'field': 'foto',          'width': 14, 'is_image': True,  'align': 'center'},
            {'header': 'Nombre',        'field': 'nombre',        'width': 35, 'is_image': False, 'align': 'left'},
            {'header': 'Num Empleado',  'field': 'num_empleado',  'width': 16, 'is_image': False, 'align': 'left'},
            {'header': 'RFC',           'field': 'rfc',           'width': 18, 'is_image': False, 'align': 'left'},
            {'header': 'Puesto',        'field': 'puesto',        'width': 30, 'is_image': False, 'align': 'left'},
            {'header': 'Adscripción',   'field': 'adscripcion',   'width': 30, 'is_image': False, 'align': 'left'},
        ]

        worksheet.set_row(0, 28)
        for c_idx, col in enumerate(COLUMNS):
            worksheet.write(0, c_idx, col['header'], hdr_fmt)
            worksheet.set_column(c_idx, c_idx, col['width'])

        # ── 5. Filas de datos ────────────────────────────────────────────
        for row_idx, empleado in enumerate(page_qs.iterator(chunk_size=200), start=1):
            worksheet.set_row(row_idx, ROW_HEIGHT_PTS)

            for c_idx, col in enumerate(COLUMNS):
                if col['is_image']:
                    foto_bytes = fotos_map.get(str(empleado.num_empleado))
                    if foto_bytes:
                        _insertar_foto(worksheet, row_idx, c_idx, foto_bytes)
                    else:
                        worksheet.write(row_idx, c_idx, '', ctr_fmt)
                    continue

                valor = getattr(empleado, col['field'], '') or ''
                fmt = {'left': left_fmt, 'right': right_fmt, 'center': ctr_fmt}.get(
                    col['align'], left_fmt
                )
                worksheet.write(row_idx, c_idx, valor, fmt)

        workbook.close()

        # ── 6. Leer y devolver ───────────────────────────────────────────
        with open(tmp_path, 'rb') as f:
            content = f.read()

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    fecha     = datetime.date.today().strftime('%d-%m-%Y')
    filename  = f"empleados_{fecha}.xlsm"
    response  = HttpResponse(
        content,
        content_type='application/vnd.ms-excel.sheet.macroEnabled.12',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
```

### Registrar la URL

```python
# urls.py
from .views import exportar_excel_empleados

urlpatterns = [
    ...
    path('api/exportar-excel-empleados/', exportar_excel_empleados, name='exportar_excel'),
]
```

---

## 7. Variante: 10 000 empleados en múltiples hojas

Para volúmenes grandes, se divide automáticamente en hojas de `ROWS_PER_SHEET` filas.

```python
ROWS_PER_SHEET = 1000   # filas de datos por hoja (ajustable)

@api_view(['GET'])
def exportar_excel_empleados_masivo(request):
    """Genera un .xlsm con todos los empleados, divididos en hojas de 1000."""
    from django.db.models import Q
    
    queryset = Empleado.objects.all().order_by('num_empleado').only(
        'num_empleado', 'nombre', 'rfc', 'puesto', 'adscripcion'
    )

    # Pre-cargar TODOS los números para la lectura paralela de fotos
    todos_los_numeros = list(queryset.values_list('num_empleado', flat=True))

    def _cargar(num):
        return num, _leer_foto(num)

    fotos_map = {}
    with ThreadPoolExecutor(max_workers=FOTOS_WORKERS) as pool:
        for num, foto in pool.map(_cargar, todos_los_numeros):
            if foto:
                fotos_map[str(num)] = foto

    if not VBA_BIN_PATH.exists():
        return Response({'detail': 'No se encontró vbaProject.bin'}, status=500)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.xlsm')
    os.close(tmp_fd)

    try:
        workbook = xlsxwriter.Workbook(tmp_path)
        workbook.add_vba_project(str(VBA_BIN_PATH))

        hdr_fmt  = workbook.add_format({'bold': True, 'font_color': '#FFFFFF',
                                         'bg_color': '#265B4E', 'align': 'center',
                                         'valign': 'vcenter', 'border': 1})
        left_fmt  = workbook.add_format({'align': 'left',   'valign': 'vcenter'})
        ctr_fmt   = workbook.add_format({'align': 'center', 'valign': 'vcenter'})

        COLUMNS = [
            {'header': 'Foto',         'field': 'foto',         'width': 14, 'is_image': True},
            {'header': 'Nombre',       'field': 'nombre',       'width': 35},
            {'header': 'Num Empleado', 'field': 'num_empleado', 'width': 16},
            {'header': 'RFC',          'field': 'rfc',          'width': 18},
            {'header': 'Puesto',       'field': 'puesto',       'width': 30},
            {'header': 'Adscripción',  'field': 'adscripcion',  'width': 30},
        ]

        total = queryset.count()
        num_hojas = (total + ROWS_PER_SHEET - 1) // ROWS_PER_SHEET

        for hoja_idx in range(num_hojas):
            offset   = hoja_idx * ROWS_PER_SHEET
            chunk    = queryset[offset: offset + ROWS_PER_SHEET]
            nombre_hoja = f"Empleados {hoja_idx * ROWS_PER_SHEET + 1}-{min((hoja_idx + 1) * ROWS_PER_SHEET, total)}"
            ws = workbook.add_worksheet(nombre_hoja)

            ws.set_row(0, 28)
            for c_idx, col in enumerate(COLUMNS):
                ws.write(0, c_idx, col['header'], hdr_fmt)
                ws.set_column(c_idx, c_idx, col['width'])

            for row_idx, emp in enumerate(chunk.iterator(chunk_size=200), start=1):
                ws.set_row(row_idx, ROW_HEIGHT_PTS)
                for c_idx, col in enumerate(COLUMNS):
                    if col.get('is_image'):
                        foto_bytes = fotos_map.get(str(emp.num_empleado))
                        if foto_bytes:
                            _insertar_foto(ws, row_idx, c_idx, foto_bytes)
                        else:
                            ws.write(row_idx, c_idx, '', ctr_fmt)
                    else:
                        valor = getattr(emp, col['field'], '') or ''
                        ws.write(row_idx, c_idx, valor, left_fmt)

        workbook.close()

        with open(tmp_path, 'rb') as f:
            content = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    fecha    = datetime.date.today().strftime('%d-%m-%Y')
    response = HttpResponse(
        content,
        content_type='application/vnd.ms-excel.sheet.macroEnabled.12',
    )
    response['Content-Disposition'] = f'attachment; filename="empleados_completo_{fecha}.xlsm"'
    return response
```

---

## 8. URL del endpoint y conexión desde Angular

### Llamada desde Angular (HttpClient)

```typescript
// empleado.service.ts
exportarExcel(params: any = {}): Observable<Blob> {
  const httpParams = new HttpParams({ fromObject: params });
  return this.http.get('/api/exportar-excel-empleados/', {
    params: httpParams,
    responseType: 'blob',
  });
}
```

### Componente Angular — disparar la descarga

```typescript
descargarExcel(): void {
  this.loading = true;
  this.empleadoService.exportarExcel({ search: this.filtro }).subscribe({
    next: (blob) => {
      const url  = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href     = url;
      link.download  = `empleados_${new Date().toLocaleDateString('es-MX')}.xlsm`;
      link.click();
      URL.revokeObjectURL(url);
      this.loading = false;
    },
    error: () => {
      this.utils.MuestraErrorInterno('Error al generar el Excel');
      this.loading = false;
    },
  });
}
```

---

## 9. Checklist de integración

```
[ ] pip install xlsxwriter Pillow  (o agregar a requirements.txt)
[ ] Crear carpeta:  tu_back/ws_tuapp/resources/fotos/
[ ] Copiar vbaProject.bin a:  tu_back/ws_tuapp/resources/vbaProject.bin
    └─ Fuente: siorh/back/SIORH-Back/ws_siorh/resources/vbaProject.bin
[ ] Agregar las funciones helper (_leer_foto, _calcular_escala, _insertar_foto)
[ ] Agregar la vista exportar_excel_empleados (o la variante masiva)
[ ] Registrar la URL en urls.py
[ ] Ajustar COLUMNS según los campos de tu modelo Empleado
[ ] Ajustar FOTOS_DIR al path real donde vivirán las fotos
[ ] Subir las fotos al servidor con nombre = num_empleado.jpg
[ ] Probar con curl:
      curl -OJ "http://tuservidor/api/exportar-excel-empleados/"
[ ] Abrir el .xlsm en Excel y verificar:
      - Las fotos están dentro de las celdas
      - Al aplicar un filtro, las fotos se desplazan con las filas
```

---

## Referencia rápida de parámetros clave

| Parámetro | Valor | Significado |
|---|---|---|
| `object_position` | `1` | `xlMoveAndSize` — imagen anclada a la celda |
| `object_position` | `2` | `xlMove` — se mueve pero no redimensiona |
| `object_position` | `3` | `xlFreeFloating` — imagen libre, no sigue filas |
| `x_offset` / `y_offset` | `3` | Margen interno de 3px dentro de la celda |
| `content_type` | `application/vnd.ms-excel.sheet.macroEnabled.12` | MIME correcto para `.xlsm` |
| Extensión de salida | `.xlsm` | Obligatoria para que Excel cargue macros |
