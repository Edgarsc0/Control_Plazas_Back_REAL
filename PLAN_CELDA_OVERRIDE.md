# Plan: CeldaOverride — edición manual de celdas sobre tablas ZAFIRO truncadas

## 1. Diagnóstico (datos reales, validados directo en MySQL `168.231.73.222`)

Las 4 tablas fuente que alimenta `importar_zafiro` **no tienen una llave de negocio
100% limpia y libre de duplicados**, porque los datos vienen de un export externo
(ZAFIRO) con ruido propio:

- **`EMPLEADOS_COMPLETOS_SIG`**: PK real es `id` AUTO_INCREMENT (lo único único).
  `Id Empleado` es buena clave de negocio para empleados con plaza ocupada, pero
  ~3000 filas la traen en blanco (posiciones vacantes) → para esas hay que usar
  `Posición` como clave alterna.
- **`BAJAS_SIG`**: PK real es `id` AUTO_INCREMENT. `NO_EMPLEADO` **no tiene
  duplicados** → es la mejor clave de negocio de las 4 tablas.
- **`MOV_POS`**: PK real es `id`. `Nº Pos Actual` se repite muchísimo (hasta 16
  veces) porque la tabla guarda histórico de movimientos por posición. Probado
  `(Nº Pos Actual, F Efva)` como clave compuesta: reduce casi todos los
  duplicados pero quedan ~decenas de choques exactos (mismo puesto, misma fecha
  efectiva, dos filas — ruido del propio ZAFIRO).
- **`cp_tbl_mov_completo_29_05_26`**: el modelo Django declara `posicion` como
  `primary_key=True`, pero la tabla es `managed=False` y en MySQL **no tiene
  ninguna PK ni índice único real**. `posicion` se repite hasta 42 veces (es
  histórico). Probado `(posicion, fecha_efectiva, sec)`: sigue habiendo algunos
  choques exactos.

**Conclusión clave**: cualquier plan que asuma "agrego PRIMARY KEY y ya" se va
a romper en producción con `IntegrityError` o sobreescritura silenciosa de
filas distintas.

### Por qué truncar es el problema real

`importar_zafiro` hace TRUNCATE + bulk_create (vía swap blue-green) cada 30
min. El `id` AUTO_INCREMENT se reparte de nuevo según el orden del CSV en cada
corrida — **no es estable entre importaciones**. Cualquier edición que el
usuario guarde apuntando a un `id` quedará huérfana o, peor, apuntando a una
fila distinta en la siguiente corrida.

## 2. Plan recomendado: tabla de "overrides" + merge en lectura

Idea central: **no tocar las tablas truncadas**. Las ediciones manuales viven
en una tabla nueva y propia; se "inyectan" sobre los datos de ZAFIRO en el
momento de leer, sin que la importación cada 30 min se entere de que existen.

### 2.1 Tabla nueva `CeldaOverride` (EAV, una sola tabla para las 4 fuentes)

```python
class CeldaOverride(models.Model):
    tabla = models.CharField(max_length=64, choices=[
        ("EMPLEADOS_COMPLETOS_SIG", "Empleados"),
        ("BAJAS_SIG", "Bajas"),
        ("MOV_POS", "Movimientos Posición"),
        ("CP_TBL_HISTORIAL", "Histórico Movimientos"),
    ])
    clave_negocio = models.JSONField()      # ej. {"id_empleado": "12345"}
                                             # ej. {"posicion": "...", "f_efva": "..."}
    clave_negocio_hash = models.CharField(max_length=64, db_index=True)  # hash determinista de clave_negocio, para indexar
    columna = models.CharField(max_length=128)   # nombre del campo editado
    valor_original = models.TextField(null=True) # snapshot al momento de editar (auditoría/diff)
    valor_nuevo = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)  # permite "revertir" sin borrar historial

    class Meta:
        indexes = [
            models.Index(fields=["tabla", "clave_negocio_hash", "columna", "activo"]),
        ]
        constraints = [
            # único override activo por (tabla, clave_negocio_hash, columna)
            models.UniqueConstraint(
                fields=["tabla", "clave_negocio_hash", "columna"],
                condition=models.Q(activo=True),
                name="uniq_override_activo",
            ),
        ]
```

Notas:
- `clave_negocio_hash` se calcula con `hashlib.sha256(json.dumps(clave_negocio, sort_keys=True))` para poder indexar/filtrar rápido sin depender de comparación de JSON.
- Esta tabla es nueva y propia (`managed=True`), no toca el esquema legacy de
  ZAFIRO — **cero riesgo para la importación**.
- Vive en la app `plantilla` (`plantilla/models.py`), junto al resto del
  dominio que ya sirve `plantilla_empleados` en el front.

### 2.2 Claves de negocio a usar por tabla

| Tabla | Clave primaria de negocio | Fallback / nota |
|---|---|---|
| `EMPLEADOS_COMPLETOS_SIG` | `Id Empleado` | si vacío → usar `Posición` |
| `BAJAS_SIG` | `NO_EMPLEADO` | confirmado sin duplicados |
| `MOV_POS` | `(Nº Pos Actual, F Efva)` | choques residuales → ver §2.5 |
| `cp_tbl_mov_completo_29_05_26` | `(posicion, fecha_efectiva, sec)` | choques residuales → ver §2.5 |

### 2.3 Aplicar overrides en LECTURA, no reescribiendo la tabla truncada

En vez de re-aplicar ediciones después del swap (lo cual agregaría UPDATEs
costosos a una tarea Celery que ya tarda y se ejecuta cada 30 min, con riesgo
de quedar a medias si crashea), el flujo es:

- Crear un helper `aplicar_overrides(filas: list[dict], tabla: str)` que,
  después de cualquier query a las 4 tablas (`views.py`,
  `obtener_posiciones_activas`, generación de Excel, etc.), busca los
  overrides activos de esa `tabla`, los indexa por `clave_negocio_hash` y
  sobreescribe en memoria los campos editados antes de devolver al frontend.
- Ventaja: el dato "verdad ZAFIRO" nunca se pierde (queda en `valor_original`
  / en la tabla real), y la importación de cada 30 min no se entera de que
  existen overrides — sigue truncando igual de rápido.
- Costo: O(N) en Python sobre filas ya traídas; los overrides serán muchísimos
  menos que las filas (miles vs decenas de miles), así que es barato.
- Hay que identificar **todos** los call-sites que leen estas 4 tablas
  (`views.py`, el endpoint que sirve `ClientComponent.jsx`,
  `generar_excel_estatus_task`) y pasarlos por este helper — ubicar con
  `cavecrew-investigator` antes de implementar.

### 2.4 Flujo de edición desde el frontend

Hoy `_hooks/useCellSelection.js` (en `eje_central_front`) ya tiene selección
de celda y modal de detalle, pero **solo lectura** — no hay PATCH. Falta
agregar:

- Endpoint `PATCH /api/plantilla/<tabla>/override/` con body:
  ```json
  {"clave_negocio": {...}, "columna": "estado_nomina", "valor_nuevo": "Activo"}
  ```
- Backend valida que la clave exista actualmente en la tabla activa, captura
  `valor_original` real (consultando la fila viva), hace upsert en
  `CeldaOverride` (desactiva el override previo si existía, crea uno nuevo —
  o reutiliza la fila si se permite editar in-place, a decidir según si se
  quiere preservar el historial fino de cada edición o solo el último valor).
- Frontend: al guardar, refleja el cambio optimistamente y marca la celda como
  "editada manualmente" (badge) usando un flag `_overridden` que el backend ya
  incluye en el merge de lectura. Botón "revertir a valor importado" → `DELETE`
  o `activo=False`.

### 2.5 Qué hacer con los choques de clave (filas indistinguibles)

Para `MOV_POS` y el histórico, unas decenas de grupos comparten clave
compuesta exacta (es ruido en el CSV fuente, no error nuestro). Dos opciones:

- **Opción A (simple, recomendada para arrancar)**: el override se aplica a
  *todas* las filas del grupo (mismo cambio se ve replicado). Aceptable si son
  pocos casos y el campo editado normalmente no varía entre ellas. Cubre el
  99% de los casos reales.
- **Opción B (más fina, documentar para después)**: al crear el override,
  guardar también un hash de columnas extra no editables (snapshot de 3-4
  columnas estables) como desambiguador adicional, y solo aplicar si ese hash
  sigue coincidiendo en la importación siguiente; si no coincide, marcar el
  override como "huérfano/ambiguo" para revisión manual.

## 3. Pasos de implementación (orden sugerido)

1. **Management command de auditoría**: reporta duplicados de clave de
   negocio por tabla (consultas ya validadas en el diagnóstico §1) — útil para
   que el equipo de datos sepa qué tan sucio está el CSV fuente.
2. **Migración**: crear modelo `CeldaOverride` + índice único + constraint
   condicional `activo=True` (ver §2.1).
3. **Helpers compartidos** en `plantilla/overrides.py`:
   - `resolve_business_key(tabla: str, fila: dict) -> dict` — aplica la regla
     de §2.2 (con fallback de `EMPLEADOS_COMPLETOS_SIG`).
   - `aplicar_overrides(filas: list[dict], tabla: str) -> list[dict]` — merge
     en lectura (§2.3).
   - `registrar_override(tabla, clave_negocio, columna, valor_nuevo,
     usuario) -> CeldaOverride` — valida, captura `valor_original`, hace
     upsert.
4. **Conectar el helper** en los endpoints de lectura que alimentan
   `plantilla_empleados` (uno a la vez, empezando por el tab que más se use).
5. **Endpoint PATCH** + permisos (¿quién puede editar? — pendiente, ver §4).
6. **UI**: celda editable + badge "editado" + botón revertir, en
   `eje_central_front/.../plantilla_empleados/_components/tabs/*` y el modal
   existente de `useCellSelection`.
7. **Vista/admin para overrides huérfanos** (clave de negocio que ya no
   aparece en la importación más reciente — empleado que causó baja, posición
   eliminada, etc.) con política de expiración o limpieza manual.

## 4. Preguntas abiertas (pendientes de decisión del usuario antes de implementar)

- ¿Quién puede editar celdas? ¿Todos los usuarios del dashboard o solo
  ciertos roles?
- Si ZAFIRO trae un valor nuevo en una celda ya editada manualmente, ¿el
  override gana siempre, o debe haber una bandera de "conflicto" visible para
  que alguien revise?
- ¿Se acepta la Opción A (override aplica a todo el grupo en los pocos casos
  de clave duplicada, §2.5) o se prefiere invertir en la Opción B (hash
  desambiguador) desde el inicio?

## 5. Referencias de ubicación en el repo

- Backend: app `plantilla` (`eje_central_back/plantilla/`) — `models.py`,
  `views.py`, `tasks.py` (incluye `importar_zafiro` / Celery beat cada 30
  min), nuevo módulo `overrides.py`.
- Frontend: `eje_central_front/src/app/dashboard/plantilla_empleados/`,
  hook `_hooks/useCellSelection.js`, tabs en `_components/tabs/*`.
