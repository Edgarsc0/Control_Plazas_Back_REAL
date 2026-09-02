"""
Helpers compartidos para generar Excel con fotografías de empleados
embebidas DENTRO de la celda (ver excel_fotos_vba_guide.md en la raíz del
repo, que documenta la técnica original de SIORH).

Clave técnica (de la guía): ``object_position=1`` (xlMoveAndSize) al insertar
la imagen es lo que realmente ancla la foto a su celda para que se desplace
junto con la fila al filtrar en Excel — la macro VBA (``vbaProject.bin``,
inyectada vía ``workbook.add_vba_project``) es solo un seguro adicional que
reaplica ese mismo ancla al abrir el archivo (``Auto_Open`` -> ``AnclarFotos``),
no el mecanismo real.

``resolver_foto_empleado`` es la MISMA lógica de resolución que ya usa
``EmpleadoFotoView`` (variantes de zero-padding + fallback a
``EmpleadoFotoAlias``) — extraída aquí para que la vista de foto individual
y los exports masivos con fotos no la dupliquen.
"""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image as PILImage

FOTOS_EMPLEADOS_DIR = Path(settings.MEDIA_ROOT) / "empleados_fotos"
FOTOS_EMPLEADOS_EXTENSIONES = ("jpg", "jpeg", "png", "JPG", "JPEG", "PNG")

VBA_BIN_PATH = Path(__file__).resolve().parent.parent / "vbaProject.bin"

# TEMPORAL — desactivado a pedido del usuario para probar que
# object_position=1 por sí solo (sin la macro VBA) ya ancla la foto a la
# celda y sobrevive al filtrado en Excel real. Volver a poner en True para
# reactivar la macro (el "seguro adicional") una vez confirmado.
VBA_HABILITADO = False

# Tamaño real de recompresión (no solo escala visual) — con esto cada foto
# pasa de ~54KB a unos pocos KB. Sin esto, un export de ~10,400 filas
# embebería los archivos originales completos (~560MB crudos).
#
# Dos perillas independientes si se quiere ajustar la calidad:
#   - FOTO_MAX_W_PX / FOTO_MAX_H_PX: resolución real de la foto (más grande
#     = más nítida, pero pesa más y tarda más en generarse/descargarse —
#     esta es la perilla "cara").
#   - FOTO_JPEG_QUALITY: compresión JPEG (0-100). Subir esto es casi gratis
#     en tiempo/tamaño hasta ~85-90 (rendimientos decrecientes arriba de
#     eso) — es la forma más barata de mejorar la calidad visible.
FOTO_MAX_W_PX = 90
FOTO_MAX_H_PX = 72
FOTO_JPEG_QUALITY = 85
# I/O-bound (existencia/lectura de archivo en disco), no CPU-bound — medido
# en la máquina de desarrollo: 8 hilos = ~49s, 24 = ~33s, 48 = ~26s para
# 13,254 fotos. Se deja en 32 como punto medio razonable sin sobreajustar a
# un solo benchmark (el disco de producción puede comportarse distinto).
FOTOS_WORKERS = 32


def _variantes_numempleado(numempleado):
    """``dict.fromkeys`` en vez de un ``set`` para no perder el orden de
    prioridad (probar primero tal cual, luego sin ceros) — un ``set`` aquí
    haría el orden de prueba no determinista. Idéntico a
    ``EmpleadoFotoView._variantes_numempleado``."""
    numempleado = str(numempleado).strip()
    sin_ceros = numempleado.lstrip("0") or "0"
    return dict.fromkeys([numempleado, sin_ceros, numempleado.zfill(11)])


def resolver_foto_empleado(numempleado):
    """Devuelve la ``Path`` a la fotografía de ``numempleado`` en disco, o
    ``None`` si no existe. Resuelve en este orden:

      1. Archivo ``<numempleado>.<ext>`` directo (variantes de zero-padding).
      2. RFC EN VIVO: SICRE nombra la foto por RFC (sin homoclave, 10
         caracteres) mientras el empleado todavía no tiene numempleado
         asignado, y la RENOMBRA sola a ``<numempleado>.<ext>`` en cuanto sí
         lo tiene — es decir, cuál de las dos convenciones aplica cambia solo
         con el tiempo, sin que nadie actualice nada de este lado. Por eso
         esto se calcula al vuelo contra el RFC actual en BD en cada llamada
         en vez de precomputarse: un alias guardado en tabla se volvería
         obsoleto en cuanto SICRE haga ese rename (seguiría apuntando al
         archivo viejo, que además desaparece del disco al siguiente rsync
         --delete). Sin caché de por medio, no hay nada que quede desfasado.
      3. Alias histórico en ``EmpleadoFotoAlias`` — red de seguridad para
         casos irregulares que ni 1 ni 2 cubren (ver
         ``cargar_fotos_empleados``), no la vía principal.
    """
    from .models import EmpleadoFotoAlias, EmpleadosCompletosSig

    numempleado = str(numempleado or "").strip()
    if not numempleado:
        return None

    for variante in _variantes_numempleado(numempleado):
        for ext in FOTOS_EMPLEADOS_EXTENSIONES:
            candidato = FOTOS_EMPLEADOS_DIR / f"{variante}.{ext}"
            if candidato.is_file():
                return candidato

    rfc = (
        EmpleadosCompletosSig.objects.filter(numempleado=numempleado)
        .exclude(rfc__isnull=True)
        .exclude(rfc="")
        .exclude(rfc=" ")
        .values_list("rfc", flat=True)
        .first()
    )
    if rfc:
        # El archivo se nombra con el RFC SIN homoclave (10 caracteres: 4
        # letras + 6 dígitos); el de BD sí trae la homoclave completa (13) —
        # mismo criterio de recorte que ya usa `cargar_fotos_empleados`.
        rfc_sin_homoclave = rfc.strip().upper()[:10]
        if rfc_sin_homoclave:
            for ext in FOTOS_EMPLEADOS_EXTENSIONES:
                candidato = FOTOS_EMPLEADOS_DIR / f"{rfc_sin_homoclave}.{ext}"
                if candidato.is_file():
                    return candidato

    alias = EmpleadoFotoAlias.objects.filter(numempleado=numempleado).first()
    if alias:
        candidato = FOTOS_EMPLEADOS_DIR / alias.nombre_archivo
        if candidato.is_file():
            return candidato

    return None


def redimensionar_foto_para_excel(ruta):
    """Abre la foto en ``ruta``, la redimensiona a
    ``FOTO_MAX_W_PX x FOTO_MAX_H_PX`` (conservando proporción) y la
    recomprime a JPEG — devuelve un ``BytesIO`` listo para insertar, o
    ``None`` si el archivo no se pudo leer/decodificar."""
    try:
        with PILImage.open(ruta) as img:
            img = img.convert("RGB")
            img.thumbnail((FOTO_MAX_W_PX, FOTO_MAX_H_PX), PILImage.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=FOTO_JPEG_QUALITY)
            buf.seek(0)
            return buf
    except Exception:
        return None


def precargar_fotos_paralelo(numempleados, max_workers=FOTOS_WORKERS):
    """Resuelve + redimensiona en paralelo (I/O-bound, no bloqueado por el
    GIL) las fotos de una lista de numempleado. Devuelve
    ``{numempleado: BytesIO}`` solo para los que sí tienen foto. Debe
    correr ANTES del loop de escritura del workbook — la escritura a
    xlsxwriter es secuencial, pero la lectura+redimensión de disco no."""
    def _cargar(num):
        ruta = resolver_foto_empleado(num)
        if not ruta:
            return num, None
        return num, redimensionar_foto_para_excel(ruta)

    numeros_unicos = list(dict.fromkeys(str(n) for n in numempleados if n))
    resultado = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for num, foto in executor.map(_cargar, numeros_unicos):
            if foto:
                resultado[num] = foto
    return resultado


def insertar_foto_en_celda(worksheet, row, col, foto_bytesio):
    """Inserta ``foto_bytesio`` anclada a (row, col) con
    ``object_position=1`` (xlMoveAndSize) — esto, no la macro VBA, es lo que
    hace que la foto se desplace junto con su fila al filtrar en Excel."""
    foto_bytesio.seek(0)
    worksheet.insert_image(row, col, "foto.jpg", {
        "image_data": foto_bytesio,
        "x_offset": 3,
        "y_offset": 3,
        "object_position": 1,
    })


def escribir_letterhead_xlsx(workbook, worksheet, num_cols, extra_legend=None):
    """Réplica en xlsxwriter del membretado institucional (misma fuente que
    ``excel_letterhead.py``, la versión openpyxl que ya usan los demás
    exports server-side, y ``excelLetterhead.js`` en el frontend) — mismo
    logo, título de 3 líneas, leyenda de fecha/hora y colores. Debe llamarse
    ANTES de escribir cualquier otro contenido; el contenido real arranca en
    la fila devuelta (0-indexed).

    ``extra_legend`` (ej. "Plantilla histórica al DD/MM/AAAA") agrega una
    fila extra bajo la leyenda de generación — usado por el export histórico
    con fotos para dejar constancia de qué representan los datos, igual que
    ``excelLetterhead.js`` en el front. Por default ``None`` (sin fila extra,
    comportamiento idéntico al de siempre)."""
    from .excel_letterhead import LOGO_PATH, TITLE_LINES, LETTERHEAD_ROWS, _fecha_hora_generacion

    num_cols = max(num_cols, 1)

    with PILImage.open(LOGO_PATH) as logo:
        orig_w, orig_h = logo.size
    display_w = 260
    display_h = round(display_w * orig_h / orig_w)

    worksheet.set_row(0, max(round(display_h * 0.85), 34))
    worksheet.insert_image(0, 0, LOGO_PATH, {
        "x_offset": 2, "y_offset": 2,
        "x_scale": display_w / orig_w,
        "y_scale": display_h / orig_h,
    })

    title_format = workbook.add_format({
        "bold": True, "font_size": 11, "font_name": "Calibri",
        "font_color": "#621F32", "align": "center", "valign": "vcenter", "text_wrap": True,
    })
    worksheet.merge_range(1, 0, 1, num_cols - 1, "\n".join(TITLE_LINES), title_format)
    worksheet.set_row(1, 54)

    legend_format = workbook.add_format({
        "italic": True, "font_size": 9, "font_name": "Calibri",
        "font_color": "#64748B", "align": "center", "valign": "vcenter",
    })
    worksheet.merge_range(
        2, 0, 2, num_cols - 1,
        f"Reporte generado por el sistema de control de plazas a las {_fecha_hora_generacion()}.",
        legend_format,
    )
    worksheet.set_row(2, 18)

    next_row = 3
    if extra_legend:
        extra_format = workbook.add_format({
            "bold": True, "italic": True, "font_size": 9, "font_name": "Calibri",
            "font_color": "#621F32", "align": "center", "valign": "vcenter",
        })
        worksheet.merge_range(next_row, 0, next_row, num_cols - 1, extra_legend, extra_format)
        worksheet.set_row(next_row, 18)
        next_row += 1

    worksheet.set_row(next_row, 8)

    return next_row + 1 if extra_legend else LETTERHEAD_ROWS


def generar_workbook_excel_con_fotos(
    *, columnas, rows, incluir_fotos, sheet_name,
    numero_empleado_key="numempleado", mono_keys=(),
    estado_nomina_key=None, mapear_estado_nomina=None,
    extra_legend=None,
):
    """Arma un workbook xlsxwriter con el membretado institucional + una
    tabla de ``columnas`` sobre ``rows`` (lista de dicts), con una columna
    "Foto" al inicio si ``incluir_fotos`` es True. Devuelve un ``BytesIO``
    listo para responder como descarga.

    Compartido por los 3 exports de Fase 1 (Detalle, Movimientos, Bajas) —
    cada vista solo resuelve SUS filas y llama aquí; el armado del archivo
    (letterhead, formato, fotos) vive en un solo lugar."""
    import xlsxwriter

    buffer = BytesIO()
    num_cols = len(columnas) + (1 if incluir_fotos else 0)
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    if incluir_fotos and VBA_HABILITADO and VBA_BIN_PATH.exists():
        workbook.add_vba_project(str(VBA_BIN_PATH))
    worksheet = workbook.add_worksheet(sheet_name[:31])

    header_row = escribir_letterhead_xlsx(workbook, worksheet, num_cols, extra_legend=extra_legend)

    header_fmt = workbook.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#2B4C7E",
        "align": "center", "valign": "vcenter", "border": 1, "border_color": "#BC955C",
    })
    base_fmt = {
        "valign": "vcenter", "border": 1, "border_color": "#BC955C",
        "font_name": "Segoe UI", "font_size": 9,
    }
    fmt_left = workbook.add_format({**base_fmt, "align": "left"})
    fmt_center = workbook.add_format({**base_fmt, "align": "center"})
    fmt_left_zebra = workbook.add_format({**base_fmt, "align": "left", "bg_color": "#F4F7FA"})
    fmt_center_zebra = workbook.add_format({**base_fmt, "align": "center", "bg_color": "#F4F7FA"})

    worksheet.set_row(header_row, 24)
    col_offset = 1 if incluir_fotos else 0
    if incluir_fotos:
        worksheet.write(header_row, 0, "Foto", header_fmt)
        worksheet.set_column(0, 0, 14)
    for i, col in enumerate(columnas):
        worksheet.write(header_row, i + col_offset, col.get("label") or col.get("key", ""), header_fmt)
        worksheet.set_column(i + col_offset, i + col_offset, 15)

    fotos_map = {}
    if incluir_fotos:
        numeros = [row.get(numero_empleado_key) for row in rows]
        fotos_map = precargar_fotos_paralelo(numeros)

    mono_keys = set(mono_keys)
    for offset, row in enumerate(rows):
        row_idx = header_row + 1 + offset
        is_zebra = offset % 2 == 1
        if incluir_fotos:
            worksheet.set_row(row_idx, 60)
            numero = str(row.get(numero_empleado_key) or "")
            foto = fotos_map.get(numero)
            if foto:
                insertar_foto_en_celda(worksheet, row_idx, 0, foto)
        for i, col in enumerate(columnas):
            key = col["key"]
            value = row.get(key)
            if key == estado_nomina_key and mapear_estado_nomina:
                value = mapear_estado_nomina(value)
            if value is None:
                value = ""
            is_mono = key in mono_keys
            fmt = (fmt_center_zebra if is_zebra else fmt_center) if is_mono else (fmt_left_zebra if is_zebra else fmt_left)
            worksheet.write(row_idx, i + col_offset, str(value), fmt)

    workbook.close()
    buffer.seek(0)
    return buffer
