# Plan de implementación: edición manual de EMPLEADOS_COMPLETOS_SIG vía CeldaOverride

Ámbito de este plan: **solo** `EMPLEADOS_COMPLETOS_SIG`, clave de negocio
`{"posicion": "<valor>"}`, editado desde `PlantillaDetalleTab.jsx`. Difiere del
enfoque original de `PLAN_CELDA_OVERRIDE.md` (merge en lectura sobre las 4
tablas): aquí el usuario pidió explícitamente **escritura directa** sobre la
tabla viva + **reaplicación por Celery** tras cada import, sin merge en
lectura ni fetch tras guardar.

## 0. Confirmado en el código actual

- `EmpleadosCompletosSig.posicion` (`plantilla/models.py:456-458`, db_column
  `"Posición"`, `max_length=8`, `db_index=True`) es la clave de negocio usable
  hoy: no es PK real (`id` autoincremental sí lo es, pero se reasigna en cada
  truncate/reload), pero es estable entre importaciones y ya se usa como
  filtro en `EmpleadosCompletosActivosDetalleView`, `EmpleadosBusquedaView`,
  etc.
- El patrón "esta tabla se trunca y recarga cada 30 min, así que cualquier
  escritura manual se pierde si no se reaplica" **ya existe** en
  `plantilla/tasks.py` con `_reaplicar_prioridad_nivel_jerarquico` (paso 10,
  línea ~1060), llamado desde `importar_zafiro` justo después del swap
  blue-green y los stored procedures de post-proceso. El nuevo paso de
  reaplicación de `CeldaOverride` sigue exactamente este mismo molde.
- `CopyCellMenu.jsx` ya soporta `onPaste`/`canPaste` (menú click-derecho →
  "Pegar valor en celda") y ya hay un consumidor funcionando en
  `CatalogosEstructuraTab.jsx` (`handlePasteCell`, línea 319) que sigue el
  patrón: validar columna editable → PATCH al backend → refrescar. La
  diferencia pedida aquí es que el refresco **no** debe ser un refetch, sino
  una actualización directa del `useState` en memoria tras la confirmación
  del backend.
- `DataTable.jsx` ya invoca `onCellContextMenu(e, value, rect, row, col.key)`
  (línea 59) — trae `row` y `colKey` de fábrica. Lo único que falta en
  `PlantillaDetalleTab.jsx` es que su `handleCellContextMenu` (línea 672) los
  capture y los guarde en `contextMenu` (hoy solo guarda `{x, y, value, rect}`).
- `detalle` **no** vive en un `useState` propio: `page.jsx` (Server Component)
  lo obtiene de `VacantesService.getEmpleadosCompletosActivosDetalle()` y lo
  pasa como prop estática a `ClientComponent.jsx`, que a su vez lo reenvía tal
  cual (mismo array) a `PlantillaDetalleTab`, `EstatusTab` y `MovimientosTab`.
  Para que la edición se refleje sin fetch **y** se mantenga consistente entre
  tabs, `detalle` debe convertirse en estado local de `ClientComponent.jsx`.

## 1. Backend — modelo `CeldaOverride`

Nuevo archivo/sección en `plantilla/models.py`, tal cual lo ya validado por el
usuario:

```python
import hashlib
import json

class CeldaOverride(models.Model):
    tabla = models.CharField(max_length=64, choices=[
        ("EMPLEADOS_COMPLETOS_SIG", "Empleados"),
        ("BAJAS_SIG", "Bajas"),
        ("MOV_POS", "Movimientos Posición"),
        ("CP_TBL_HISTORIAL", "Histórico Movimientos"),
    ])
    clave_negocio = models.JSONField()
    clave_negocio_hash = models.CharField(max_length=64, db_index=True)
    columna = models.CharField(max_length=128)
    valor_original = models.TextField(null=True)
    valor_nuevo = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["tabla", "clave_negocio_hash", "columna", "activo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tabla", "clave_negocio_hash", "columna"],
                condition=models.Q(activo=True),
                name="uniq_override_activo",
            ),
        ]
```

Solo se usan los choices `EMPLEADOS_COMPLETOS_SIG` en esta fase; los otros 3
quedan declarados para no romper el diseño ya acordado, pero sin lógica
asociada todavía (no se implementa nada de BAJAS_SIG/MOV_POS/histórico aquí).

Migración estándar (`python manage.py makemigrations plantilla`).

## 2. Backend — helper `plantilla/celda_override.py` (nuevo módulo)

```python
EDITABLE_COLUMNS_EMPLEADOS = {
    f.name for f in EmpleadosCompletosSigBase._meta.get_fields()
    if f.name not in ("id", "posicion")
}

def compute_clave_hash(clave_negocio: dict) -> str:
    return hashlib.sha256(
        json.dumps(clave_negocio, sort_keys=True).encode()
    ).hexdigest()

def registrar_y_aplicar_override_empleado(posicion, columna, valor_nuevo, usuario):
    """
    Todo en una transacción:
      1. Valida `columna` contra EDITABLE_COLUMNS_EMPLEADOS.
      2. Bloquea y lee la fila viva (select_for_update) para capturar
         valor_original real (lo que se está a punto de sobreescribir,
         sea el dato original de ZAFIRO o un override previo ya aplicado).
      3. Desactiva el override activo previo de esa (tabla, clave, columna)
         si existe (activo=False, se conserva — no se borra).
      4. Crea el nuevo CeldaOverride (activo=True).
      5. Ejecuta el UPDATE directo sobre EMPLEADOS_COMPLETOS_SIG.
    Lanza ValueError si la columna no es editable o la posición no existe.
    """
    if columna not in EDITABLE_COLUMNS_EMPLEADOS:
        raise ValueError(f"Columna '{columna}' no es editable.")

    clave_negocio = {"posicion": posicion}
    clave_hash = compute_clave_hash(clave_negocio)

    with transaction.atomic():
        fila = (
            EmpleadosCompletosSig.objects
            .select_for_update()
            .filter(posicion=posicion)
            .first()
        )
        if fila is None:
            raise ValueError(f"Posición '{posicion}' no existe en EMPLEADOS_COMPLETOS_SIG.")

        valor_original = getattr(fila, columna)
        valor_original = None if valor_original is None else str(valor_original)

        CeldaOverride.objects.filter(
            tabla="EMPLEADOS_COMPLETOS_SIG",
            clave_negocio_hash=clave_hash,
            columna=columna,
            activo=True,
        ).update(activo=False)

        override = CeldaOverride.objects.create(
            tabla="EMPLEADOS_COMPLETOS_SIG",
            clave_negocio=clave_negocio,
            clave_negocio_hash=clave_hash,
            columna=columna,
            valor_original=valor_original,
            valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else None,
            usuario=usuario,
            activo=True,
        )

        EmpleadosCompletosSig.objects.filter(posicion=posicion).update(**{columna: valor_nuevo})

    return override


def aplicar_overrides_empleados_completos(bitacora=None):
    """
    Llamado por Celery tras cada import de ZAFIRO (EMPLEADOS_COMPLETOS_SIG se
    trunca y recarga completa cada 30 min). Reaplica todos los overrides
    activos sobre la tabla recién cargada. No falla si una `posicion` ya no
    existe (posición dada de baja / eliminada) — solo cuenta huérfanos.
    """
    overrides = CeldaOverride.objects.filter(
        tabla="EMPLEADOS_COMPLETOS_SIG", activo=True
    )
    aplicados, huerfanos = 0, 0
    with transaction.atomic():
        for ov in overrides:
            posicion = ov.clave_negocio.get("posicion")
            updated = EmpleadosCompletosSig.objects.filter(posicion=posicion).update(
                **{ov.columna: ov.valor_nuevo}
            )
            if updated:
                aplicados += 1
            else:
                huerfanos += 1
    return {"aplicados": aplicados, "huerfanos": huerfanos}
```

Notas:
- `select_for_update()` evita condición de carrera si dos usuarios editan la
  misma celda casi al mismo tiempo.
- El `UPDATE ... WHERE posicion=...` puede tocar más de una fila si hay
  posiciones duplicadas en `EMPLEADOS_COMPLETOS_SIG` (el diagnóstico de
  `PLAN_CELDA_OVERRIDE.md` ya documentó que puede haber posiciones vacías/
  repetidas en casos raros). Aceptado como comportamiento igual al de
  `_reaplicar_prioridad_nivel_jerarquico`, que tiene el mismo riesgo y ya está
  en producción — no se resuelve aquí, se documenta como limitación conocida.
- `valor_nuevo`/`valor_original` se guardan como texto: todas las columnas de
  `EmpleadosCompletosSigBase` son `CharField`, así que no hay pérdida de tipo.

## 3. Backend — endpoint

Nueva vista en `plantilla/views.py`:

```python
class EmpleadosCompletosCeldaOverrideView(APIView):
    view_permission = "authentication.edit_plantilla_detalle"  # o el permiso que se decida (ver §6)

    def post(self, request):
        posicion = request.data.get("posicion")
        columna = request.data.get("columna")
        valor_nuevo = request.data.get("valor_nuevo")
        if not posicion or not columna:
            return Response({"detail": "posicion y columna son requeridos."}, status=400)
        try:
            override = registrar_y_aplicar_override_empleado(
                posicion, columna, valor_nuevo, request.user
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        # Invalida las mismas cachés que invalida importar_zafiro sobre este dataset
        from django.core.cache import cache
        cache.delete_many(["empleados_completos_activos_detalle", "active_employees_filtered"])

        return Response({
            "posicion": posicion,
            "columna": columna,
            "valor_nuevo": override.valor_nuevo,
            "valor_original": override.valor_original,
            "usuario": request.user.username,
            "fecha_modificacion": override.fecha_modificacion,
        })
```

Ruta en `urls.py`:
```python
path("empleados_completos_sig/override/", EmpleadosCompletosCeldaOverrideView.as_view(), name="empleados_completos_sig_override"),
```

## 4. Backend — Celery (`plantilla/tasks.py`)

Insertar la llamada **justo después** de `_reaplicar_prioridad_nivel_jerarquico(bitacora)`
(línea 1304) y **antes** de "Generar/Actualizar Cuadro de Vacancia" (línea 1306),
mismo lugar en el flujo que su precedente directo:

```python
# ── 10.5. Reaplicar CeldaOverride sobre EMPLEADOS_COMPLETOS_SIG ────────
from .celda_override import aplicar_overrides_empleados_completos
try:
    stats = aplicar_overrides_empleados_completos(bitacora)
    _append_log(
        bitacora,
        f"CeldaOverride reaplicados: {stats['aplicados']} aplicado(s), {stats['huerfanos']} huérfano(s).",
    )
except Exception as e:
    _append_log(bitacora, f"Error reaplicando CeldaOverride: {e}", is_error=True)
    logger.error("Error en aplicar_overrides_empleados_completos: %s", e, exc_info=True)
```

Se ubica antes del bloque de invalidación de caché (línea ~1340), así que el
próximo `GET` ya sirve los valores editados sin esperar al TTL.

## 5. Frontend

### 5.1 `VacantesService.js`
```js
static async patchEmpleadoCompletoOverride(posicion, columna, valorNuevo) {
    return apiFetch(`/plantilla/empleados_completos_sig/override/`, {
        method: 'POST',
        body: JSON.stringify({ posicion, columna, valor_nuevo: valorNuevo }),
    });
}
```

### 5.2 `ClientComponent.jsx` — subir `detalle` a estado local
```js
const [detalleData, setDetalleData] = useState(detalle);
```
Reemplazar los 3 usos de `detalle={detalle}` (PlantillaDetalleTab, EstatusTab,
MovimientosTab) por `detalle={detalleData}`. Pasar además a
`PlantillaDetalleTab` una función de escritura puntual:
```js
const updateDetalleCell = useCallback((posicion, columna, valorNuevo) => {
  setDetalleData(prev => prev.map(row =>
    row.posicion === posicion ? { ...row, [columna]: valorNuevo } : row
  ));
}, []);
```
(nombre `updateDetalleCell` en vez de exponer `setDetalleData` crudo, para no
permitir mutaciones arbitrarias fuera del flujo de override).

### 5.3 `PlantillaDetalleTab.jsx`
- Recibe nueva prop `onCellEdited={updateDetalleCell}`.
- `handleCellContextMenu` (línea 672) debe capturar `row`/`colKey` igual que
  `CatalogosEstructuraTab`:
  ```js
  const handleCellContextMenu = useCallback((e, value, rect, row, colKey) => {
    setContextMenu({ x: e.clientX, y: e.clientY, value, rect, row, colKey });
  }, []);
  ```
- Whitelist de columnas editables en cliente (solo para habilitar/deshabilitar
  "Pegar valor" en el menú — la validación real vive en backend):
  ```js
  const NON_EDITABLE_KEYS = new Set(["posicion"]); // clave de negocio, no editable
  const isPasteableColumn = (colKey) => !!colKey && !NON_EDITABLE_KEYS.has(colKey);
  ```
- `handlePasteCell`:
  ```js
  const handlePasteCell = useCallback(async (text) => {
    const { row, colKey } = contextMenu || {};
    if (!row || !colKey || !isPasteableColumn(colKey)) return;
    const res = await VacantesService.patchEmpleadoCompletoOverride(row.posicion, colKey, text);
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || "No se pudo guardar el cambio.");
    }
    // Solo tras confirmación del backend se refleja en el useState — sin fetch.
    onCellEdited(row.posicion, colKey, text);
  }, [contextMenu, onCellEdited]);
  ```
- Conectar en el `<CopyCellMenu>` (línea 1358):
  ```jsx
  <CopyCellMenu
    contextMenu={contextMenu}
    onClose={() => setContextMenu(null)}
    onPaste={handlePasteCell}
    canPaste={isPasteableColumn(contextMenu?.colKey)}
  />
  ```
- `CopyCellMenu.onPaste` ya maneja su propio try/catch y estado "error" visual
  — no requiere trabajo extra ahí.

### 5.4 Alcance explícitamente fuera de esta fase
- Sin badge "editado manualmente" ni botón "revertir a valor importado" en la
  UI — no fue pedido en esta iteración. `CeldaOverride.activo=False` ya deja
  la puerta abierta para implementarlo después sin cambios de esquema.
- Sin edición para BAJAS_SIG / MOV_POS / histórico — el modelo las declara en
  `choices` pero no hay endpoint ni reaplicación Celery para ellas todavía.

## 6. Decisiones pendientes (antes de implementar)

- **Permiso de edición**: el plan usa `authentication.edit_plantilla_detalle`
  como placeholder — hay que confirmar si ese codename existe ya en
  `authentication` o si se crea uno nuevo, y si edición la tienen todos los
  que ven el tab o un subconjunto de roles.
- **Confirmación visual de error**: si el `POST` falla, `CopyCellMenu` ya
  muestra el ícono de error (`AlertTriangle`) por 1.5s vía su propio estado
  `pasteState`; no hay toast adicional salvo que se pida uno.

## 7. Orden de implementación sugerido

1. Modelo `CeldaOverride` + migración.
2. `plantilla/celda_override.py` (helper).
3. Endpoint + ruta.
4. Paso Celery en `tasks.py` (después de confirmar con datos reales que
   `aplicar_overrides_empleados_completos` no falla contra staging).
5. `VacantesService.patchEmpleadoCompletoOverride`.
6. `ClientComponent.jsx`: `detalle` → estado local + `updateDetalleCell`.
7. `PlantillaDetalleTab.jsx`: contextMenu con row/colKey, `handlePasteCell`,
   cableado de `CopyCellMenu`.
8. Prueba manual end-to-end: editar celda → verificar fila en `CeldaOverride`
   → verificar `UPDATE` en `EMPLEADOS_COMPLETOS_SIG` → forzar un
   `importar_zafiro` (o correr `aplicar_overrides_empleados_completos`
   directo) → confirmar que el valor editado sobrevive al truncate/reload.
