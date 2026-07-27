# Optimización de Consultas e Índices — DB `EjeCentral`

> Fecha: 2026-07-03 · Motor: **MySQL 8.0.45** (InnoDB) · Medido **en vivo** con `EXPLAIN ANALYZE`
> (solo lectura; no se modificó el esquema).

## Contexto: los datos son pequeños

| Tabla | Filas | Datos | Índices |
|-------|------:|------:|--------:|
| `cp_tbl_mov_completo_29_05_26` | 143.312 | 61.6 MB | 30.6 MB |
| `MOV_POS` | 51.912 | 20.6 MB | 15.1 MB |
| `EMPLEADOS_COMPLETOS_SIG` | 12.459 | 11.5 MB | 2.9 MB |
| `BAJAS_SIG` | 5.371 | 3.5 MB | 0.9 MB |
| `plantilla_1800_plazas` | 1.636 | 3.5 MB | — |
| `ORGANIGRAMA_ANAM` | 1.365 | 0.3 MB | — |

**Conclusión:** el volumen NO es el problema. El costo viene de **cómo** se consultan: una window
function con *filesort* recalculada muchas veces, y algún scan por `TRIM()`. La tabla más grande ya
está bien indexada y sus consultas usan índice. Los índices existentes (incluidos los funcionales
`Trim(col)` y el auto-generado en `EMPLEADOS_COMPLETOS_SIG.Posición`) **están correctos y en uso** —
verificado por EXPLAIN.

---

## Hallazgo dominante — window function con *filesort* (≈320 ms)

Consulta de "posiciones activas más recientes" (usada en Torre Caballito 3D/Empleados/Search, Desglose
Jerárquico, `obtener_posiciones_activas`, `LATEST_MOVPOS_RAW_SQL`):

```sql
SELECT `Nº Pos Actual` FROM (
  SELECT `Nº Pos Actual`, `Estado Psn`, ROW_NUMBER() OVER (
    PARTITION BY `Nº Pos Actual`
    ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
  ) rn FROM MOV_POS
) r WHERE rn = 1 AND `Estado Psn` = 'A';
```

`EXPLAIN ANALYZE` (real):
```
Filter rn=1 AND Estado Psn='A'   (actual time=309..320  rows=11451)
  -> Materialize (rows=52776)
    -> Window aggregate: row_number()            (actual time=254..291)
      -> Sort: Nº Pos Actual, F Efva DESC, Fecha Captura DESC, F/H Últ Actz DESC, id DESC   ← FILESORT
        -> Table scan on MOV_POS (rows=52776)     ← FULL SCAN
```

El índice actual `idx_mov_pos_actual` es `(Nº Pos Actual[prefijo 50], F Efva)`: cubre el `PARTITION BY`
pero **no** las otras 3 columnas del `ORDER BY`, así que MySQL ordena 52.776 filas en memoria/disco en
cada ejecución.

### Solución recomendada (dos niveles)

**Nivel 1 — Materializar (mayor impacto, resuelve de raíz).** Los datos solo cambian cada 30 min (import
ZAFIRO). Construir una tabla resumen al final de la tarea Celery y que los endpoints la consulten:

```sql
-- Reconstruida por la tarea Celery tras el swap blue-green:
CREATE TABLE MOV_POS_LATEST (
  id BIGINT PRIMARY KEY,
  pos_actual VARCHAR(50),
  estado_psn VARCHAR(10),
  KEY idx_mpl_pos (pos_actual),
  KEY idx_mpl_estado_pos (estado_psn, pos_actual)
);
-- INSERT ... SELECT del rn=1 (la window se corre UNA vez cada 30 min, no por request).
```
Los 6+ endpoints pasan de ~320 ms a un lookup indexado (<20 ms). Ver **BE2** en `AUDITORIA_BUGS_BACK.md`.

**Nivel 2 — Índice de cobertura (interino).** ⚠️ **Ojo con un límite real:** las 5 columnas del
`ORDER BY` (`no_pos_actual`, `f_efva`, `fecha_captura`, `fh_ult_actz`, `id`) son `VARCHAR(255)`
utf8mb4 (verificado en `models.py:754-822`). Un índice con las 5 a longitud completa **excede el
límite de 3072 bytes de InnoDB y fallaría** (`Specified key was too long`). Por eso el índice actual
`idx_mov_pos_actual` ya usa un **prefijo de 50**. Un índice interino tendría que usar prefijos:

```sql
ALTER TABLE MOV_POS
  ADD INDEX idx_movpos_latest
  (`Nº Pos Actual`(20), `F Efva`(10), `Fecha Captura`(19), `F/H Últ Actz`(20), `id`);
```

Pero un índice de **prefijo no garantiza orden** para todas las filas, así que MySQL **puede seguir
haciendo un sort parcial**: la mejora es limitada e incierta. Además guardar fechas como texto
(`VARCHAR`) es la causa de fondo. Por eso el **Nivel 1 (materializar) es la solución correcta**, no el
índice. Alternativa estructural: convertir `f_efva`/`fecha_captura`/`fh_ult_actz` a tipos `DATE`/
`DATETIME` reales y entonces sí un índice compacto elimina el filesort.

> ⚠️ **Blue-green:** `MOV_POS` se reconstruye por swap con `MOV_POS_STAGING` (ver comentarios en
> `models.py:961-963`). Cualquier índice debe declararse también en el modelo `MovPosStaging`, o se
> pierde en el siguiente import. De ahí que, si se hace, sea vía **migración Django**, no DDL suelto.

---

## Índices redundantes a eliminar — `cp_tbl_mov_completo_29_05_26`

Verificado en `information_schema.statistics`:

| Índice | Columnas | Estado |
|--------|----------|--------|
| `idx_cp_posicion` | `posicion` | 🔴 Redundante — prefijo de `idx_pos_fecha (posicion, fecha_efectiva)` |
| `idx_cp_num_empleado` | `num_empleado` | 🔴 Redundante — prefijo de `idx_emp_fecha (num_empleado, fecha_efectiva)` |

Cualquier consulta que use `idx_cp_posicion` puede usar `idx_pos_fecha` igual de bien. Mantenerlos
desperdicia espacio (parte de los 30 MB de índices) y **ralentiza el import** (esta tabla es de recarga
masiva: cada índice extra se reconstruye). Como es `managed=False`, se elimina por DDL:

```sql
ALTER TABLE cp_tbl_mov_completo_29_05_26 DROP INDEX idx_cp_posicion;
ALTER TABLE cp_tbl_mov_completo_29_05_26 DROP INDEX idx_cp_num_empleado;
-- Rollback: ADD INDEX idx_cp_posicion (posicion); ADD INDEX idx_cp_num_empleado (num_empleado);
```
(Aplicar el mismo cambio en `cp_tbl_mov_completo_29_05_26_staging` si el refresh hace swap.)

---

## Otras consultas medidas (ya correctas — no requieren acción)

- **Listado Movimientos** (`ORDER BY fecha_efectiva DESC, sec DESC LIMIT 50`): usa
  `idx_cptbl_fefec_sec (reverse)` → **~11 ms**. ✅ Óptimo.
  *Nota:* ordenar por columnas de texto **distintas** de `accion_nombre`/`motivo_nombre` (que sí tienen
  índice `Trim`) cae en *filesort* de 143k filas. Si se vuelve común ordenar por `nombre`/`ap_pat`/etc.,
  añadir índices `Trim(col)` para esas columnas.
- **JOIN Desglose** (`EMPLEADOS_COMPLETOS_SIG.Posición = MOV_POS.Nº Pos Actual`): usa el índice
  `EMPLEADOS_COMPLETOS_SIG_Posición_e8cef9a4` (~0.04 ms/lookup). ✅ El `db_index=True` del modelo **sí**
  existe en la DB.
- **`OCUPADAS_RAW_SQL`** (`TRIM(Id Empleado)<>'' OR TRIM(Nombres)<>''`): **~130 ms**, scan completo
  (el `OR`+`TRIM` impide *seek*). Está cacheada 600 s, así que el impacto es bajo. Si se quiere quitar
  el scan: columna generada `is_ocupado` (`STORED`) indexada, poblada en el import.
- **`COUNT(*)` del paginador** sobre `cp_tbl` (143k): **~40 ms** por página. Aceptable; si molesta,
  usar un contador aproximado/caché para el total.

---

## Housekeeping

Tablas de respaldo/staging acumuladas (ocupan espacio, sin uso en runtime):
`MOV_POS_bak_20260702`, `MOV_POS_bak_20260703` (backups diarios que se acumulan),
`cp_tbl_mov_completo_29_05_26_staging` (0 filas). Definir retención (p. ej. conservar 3 días de `*_bak_*`
y purgar el resto) en la tarea de import.

---

## Plan de aplicación (orden recomendado)

Todos los cambios son **online** en MySQL 8 (InnoDB, `ALGORITHM=INPLACE`) sobre tablas ≤143k filas:
segundos, sin bloquear lecturas. Aun así, **aplicar primero en staging** y en ventana de bajo tráfico.

1. **DROP** de los 2 índices redundantes en `cp_tbl_mov_completo_29_05_26` (DDL directo, `managed=False`).
   Cambio simple, sin riesgo, y acelera el import. Rollback trivial (arriba).
2. **Materializar `MOV_POS_LATEST`** en la tarea Celery y migrar los 6+ endpoints a un lookup indexado
   (mayor ganancia; ver `AUDITORIA_BUGS_BACK.md` BE2). **Este es el fix real** de la window function.
3. *(Opcional / estructural)* Convertir las columnas de fecha de `MOV_POS` de `VARCHAR` a `DATE/DATETIME`
   y, ya con tipos compactos, añadir vía **migración Django** el índice `idx_movpos_latest` en `MovPos`
   **y** `MovPosStaging`. Solo si no se hace el paso 2 o se quiere además acelerar el rebuild.
4. Housekeeping de tablas `*_bak_*`.

**Impacto esperado:** endpoints de ocupación (Torre Caballito, Desglose) de ~300 ms → <20 ms en *cache
miss* (paso 2); import de ZAFIRO más rápido al quitar índices redundantes (paso 1).

> Nota: no se aplicó ningún `ALTER`/`CREATE`/`DROP` en la DB durante esta auditoría. Las mediciones son
> de `EXPLAIN ANALYZE` (lectura). Puedo aplicar los cambios del paso 1-2 si me lo confirmas.
