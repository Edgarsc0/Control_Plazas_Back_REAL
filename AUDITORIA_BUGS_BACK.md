# Auditoría de Bugs y Rendimiento — `eje_central_back`

> Fecha: 2026-07-03 · Stack: Django + DRF + Celery + MySQL 8.0.45 · Foco: `plantilla/` (views 3410 líneas, el núcleo).

El backend está **bien construido**: SQL crudo parametrizado (sin SQLi), caché Redis en los
endpoints pesados, índices funcionales (`Trim(col)`), paginación server-side, helpers de filtro que
validan nombres de campo contra el modelo, y swap blue-green en la importación de ZAFIRO. Los
hallazgos son por tanto puntuales; el de mayor impacto es la **window function recalculada por
request**. Cada hallazgo trae `archivo:línea`, impacto y corrección. Al final, plan por fases.

Evidencia de base de datos (medida en vivo): ver `../eje_central_back/OPTIMIZACION_QUERYS_DB.md`.

---

## Resumen ejecutivo

| # | Hallazgo | Severidad | Tipo |
|---|----------|-----------|------|
| BE1 | Invalidación de caché incompleta tras import ZAFIRO (claves hasheadas nunca se borran) | 🔴 Alta | Bug datos |
| BE2 | Window function "posiciones activas" recalculada por request (~300 ms) en 6+ endpoints | 🔴 Alta | Perf |
| BE3 | Respuestas de error devuelven `str(e)` al cliente (fuga de internals) | 🟠 Media | Seguridad |
| BE4 | Config insegura: `SECRET_KEY` fallback, `ALLOWED_HOSTS=['*']`, BrowsableAPI en prod | 🟠 Media | Seguridad |
| BE5 | Endpoints sin paginar devuelven tablas completas (12k filas) | 🟠 Media | Perf |
| BE6 | Nombre de tabla congelado `cp_tbl_mov_completo_29_05_26` hardcodeado en modelo | 🟠 Media | Mantenibilidad |
| BE7 | `no_pagination=true` / `max_page_size=10000` serializan toda la tabla | 🟡 Baja | Perf |
| BE8 | `except Exception: pass` y búsquedas OR-`icontains` sin índice | 🟡 Baja | Robustez/Perf |

---

## 🔴 Correctitud / datos

### BE1 — Invalidación de caché incompleta tras la importación de ZAFIRO

**Dónde:** `plantilla/tasks.py:1210-1227` (lista fija de claves a borrar) vs. las claves que las
views realmente escriben.

**Problema:** al terminar la importación (cada 30 min) se hace `cache.delete_many([...])` con una
lista **fija**, pero varias views cachean con claves que **no están** en esa lista:

1. `MovimientosPersonalStatsView` (`views.py:3269-3270`) escribe en `mov_stats_<md5>` (hash de
   `accion_nombre`/`fecha_captura__in`). La lista de invalidación borra `"movimientos_personal_stats"`,
   que **nunca se escribe** → es una clave muerta. Las estadísticas reales quedan **stale hasta 20 min**
   (su TTL de 1200 s) tras cada actualización.
2. `desglose_jerarquico` (`views.py:3356`) y `mov_pos_ocupadas_set` (`views.py:1520`) tampoco se
   invalidan → datos viejos hasta su TTL.

**Impacto:** tras una actualización de ZAFIRO, el usuario puede ver cifras desactualizadas por
10-20 min en Movimientos/Cuadros/Desglose, de forma inconsistente con el resto del dashboard (que sí
se refresca por SSE).

**Corrección:** que la invalidación borre por **patrón** además de por lista, o centralizar las
claves. Ej.:
```python
for key in r.scan_iter("*mov_stats_*"):
    r.delete(key)
cache.delete_many([..., "desglose_jerarquico", "mov_pos_ocupadas_set", "torre_caballito_3d", ...])
```
Mejor aún: definir un `CACHE_KEYS`/prefijo único por dominio y un helper `invalidate_all()` para no
volver a desalinear la lista.

---

### BE2 — La window function "posiciones activas" se recalcula por request

**Dónde:** el patrón `ROW_NUMBER() OVER (PARTITION BY 'Nº Pos Actual' ORDER BY 'F Efva' DESC, …)`
sobre **toda** `MOV_POS` aparece inline en:
- `views.py:333-341` (`LATEST_MOVPOS_RAW_SQL`), `:356-376` (`obtener_posiciones_activas`)
- `views.py:2826` (Torre 3D), `:2886`/`:2910` (Torre Empleados), `:2978` (Torre Search)
- `views.py:3381-3389` (Desglose Jerárquico)

**Evidencia medida (`EXPLAIN ANALYZE`, en vivo):**
```
Filter rn=1 AND Estado Psn='A'  (actual time=309..320  rows=11451)
  -> Materialize (rows=52776)
    -> Window aggregate: row_number() (actual time=254..291)
      -> Sort: Nº Pos Actual, F Efva DESC, Fecha Captura DESC, F/H Últ Actz DESC, id DESC
        -> Table scan on MOV_POS (rows=52776)
```
**~320 ms** por ejecución: full scan de 52.776 filas + **filesort** de 5 columnas + materialización.
`obtener_posiciones_activas` y `latest_movpos_sub_ids` sí cachean el resultado, pero los endpoints de
Torre Caballito y Desglose lo **embeben como subquery** y solo cachean el resultado final del
endpoint; en cada *cache miss* recomputan la window completa, sin poder compartir trabajo.

**Corrección (por orden de impacto):**
1. **Materializar** las "posiciones activas más recientes" en una tabla resumen (p. ej.
   `MOV_POS_LATEST` con `Nº Pos Actual`, `id`, `Estado Psn`) que la tarea Celery **reconstruye al
   final de cada import** (los datos solo cambian cada 30 min). Los endpoints hacen un `JOIN`/lookup
   indexado trivial en lugar de la window. Elimina ~300 ms de casi todos los endpoints de ocupación.
2. Interino sin cambiar el pipeline: **índice de cobertura** que evita el filesort (ver
   `OPTIMIZACION_QUERYS_DB.md`, índice `idx_movpos_latest`).
3. Que Torre/Desglose reutilicen `obtener_posiciones_activas()` (ya cacheada) en vez de reejecutar la
   subconsulta.

---

## 🟠 Seguridad / configuración

### BE3 — Las respuestas de error devuelven `str(e)` al cliente

**Dónde:** patrón repetido — p. ej. `views.py:737-740`, `:2510`, `:3344-3347`, `:3407-3410`
(`return Response({"error": str(e)}, status=500)`), y `tasks.py:1232` (`except Exception: pass`).

**Problema:** exponer el texto de la excepción filtra detalles internos (nombres de tabla/columna,
rutas) a clientes autenticados; y el `except: pass` oculta fallos de invalidación de caché.

**Corrección:** loggear el error con `logger.exception(...)` y devolver un mensaje genérico
(`{"error": "Error interno"}`). Nunca serializar `str(e)` en la respuesta.

---

### BE4 — Configuración insegura para producción

**Dónde:** `eje_central_back/settings.py`.

- `SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-…")` (`:15`) — fallback inseguro **hardcodeado**.
  Si la env falta, arranca con clave conocida (compromete firmas de sesión/tokens).
- `ALLOWED_HOSTS = ["*"]` (`:19`) — acepta cualquier Host header.
- `BrowsableAPIRenderer` en `DEFAULT_RENDERER_CLASSES` (`:184`) — expone la API navegable HTML de DRF
  en producción (superficie extra + render lento de payloads grandes).

**Corrección:** exigir `SECRET_KEY` (fallar si falta), fijar `ALLOWED_HOSTS` a los dominios reales,
y dejar solo `ORJSONRenderer` en prod (o condicionar el Browsable por `DEBUG`). Añadir
`SECURE_*`/`SESSION_COOKIE_SECURE` cuando haya TLS.

---

### BE5 — Endpoints que devuelven tablas completas sin paginar

**Dónde:** `EmpleadosCompletosActivosDetalleView` (`views.py:757` → `list(queryset.values())`, ~12k
filas), `OrganigramaSearchView` sin `q` (`views.py:2785-2789`, todo el catálogo),
`CuadroVacanciaView` (`views.py:3342`), `DesgloseJerarquicoView` (`views.py:3403`).

**Problema:** no hay `DEFAULT_PAGINATION_CLASS` global (`settings.py` REST_FRAMEWORK), así que estos
endpoints entregan el dataset entero. Es la contraparte del hallazgo **B4/B6 del front**: el cliente
recibe miles de filas y filtra/ordena en memoria. Mitigado por caché, pero el payload y el parse en el
navegador siguen siendo grandes.

**Corrección:** paginar del lado servidor (como ya hacen `MovPosDetalleView`/`MovimientosPersonalListView`)
los listados grandes, o al menos comprimir (GZip ya está activo) y recortar columnas con `.values(*campos)`.

---

### BE6 — Nombre de tabla congelado en el modelo

**Dónde:** `plantilla/models.py:1080-1081` (`db_table = "cp_tbl_mov_completo_29_05_26"`, `managed=False`),
consumido por `MovimientosPersonalListView`/`StatsView`/`HistorialView`.

**Aclaración medida:** la tabla **sí está fresca** (`MAX(fecha_captura)=2026-07-03`, hoy; 147k filas),
así que **no** es un bug de datos viejos. Pero el nombre con fecha (`_29_05_26`) está **hardcodeado**;
cualquier recreación con nombre nuevo rompe el modelo silenciosamente (`managed=False` no avisa).

**Corrección:** renombrar la tabla a un nombre estable (p. ej. `mov_completo`) y actualizar el modelo,
o exponer el nombre por settings/env. Documentar que el refresh debe conservar el nombre.

---

## 🟡 Menores

- **BE7** — `MovPosPagination`/`MovimientosPersonalPagination` con `max_page_size=10000` y la rama
  `no_pagination=true` (`views.py:3139-3141`, `1136` aprox.) serializan la tabla completa vía DRF.
  Limitar `max_page_size` y forzar exportaciones por el backend con streaming.
- **BE8** — `apply_text_search` (`views.py:61-69`) hace `OR icontains` (=`LIKE '%q%'`) sobre 7-8
  columnas: no usa índice (comodín inicial). Aceptable por tamaño+caché; si crece, evaluar índice
  FULLTEXT. Además el `COUNT(*)` del paginador sobre `cp_tbl` (~143k) cuesta ~40 ms por página.
- **Micro** — imports dentro de métodos y `_meta.get_fields()` por request; cachear a nivel módulo.

---

## Plan de corrección (por fases)

### Fase 1 — Datos correctos (alto impacto, bajo riesgo)
1. **BE1**: invalidación de caché por patrón (`*mov_stats_*`) + añadir `desglose_jerarquico`,
   `mov_pos_ocupadas_set`, torre. Quitar la clave muerta `movimientos_personal_stats`.
2. **BE3**: dejar de devolver `str(e)`; `logger.exception` + mensaje genérico.

### Fase 2 — Rendimiento (el gran salto)
3. **BE2**: materializar `MOV_POS_LATEST` en la tarea Celery y reescribir los 6 endpoints para hacer
   lookup indexado. Índice de cobertura como interino (ver doc DB).
4. **BE5/BE7**: paginar los listados grandes; recortar columnas; limitar `max_page_size`.

### Fase 3 — Seguridad / hardening
5. **BE4**: `SECRET_KEY` obligatoria, `ALLOWED_HOSTS` real, quitar Browsable en prod, cookies seguras.
6. **BE6**: renombrar la tabla congelada y ajustar el modelo.

### Fase 4 — Limpieza
7. **BE8** y micro-optimizaciones; housekeeping de tablas `*_bak_*` (ver doc DB).

**Métrica objetivo:** medir latencia p95 de los endpoints de Torre Caballito y Desglose antes/después
de materializar `MOV_POS_LATEST` (esperado: de ~300 ms a <20 ms en cache miss).
