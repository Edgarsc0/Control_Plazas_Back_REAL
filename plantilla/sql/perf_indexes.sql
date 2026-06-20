-- Índices de rendimiento para tablas NO gestionadas por Django (managed=False)
-- y mejoras opcionales. Ejecutar manualmente en MySQL:
--   mysql -u <user> -p <db> < plantilla/sql/perf_indexes.sql
--
-- Las tablas managed=True (plantilla_1800_plazas, MOV_POS) se indexan vía la
-- migración 0013 (python manage.py migrate). Este archivo cubre el resto.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. movimientos-personal (cp_tbl_mov_completo_29_05_26, managed=False)
--    Acelera el orden por defecto ORDER BY fecha_efectiva DESC, sec DESC.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE INDEX idx_cptbl_fefec_sec
    ON cp_tbl_mov_completo_29_05_26 (fecha_efectiva, sec);

-- Índices funcionales para los filtros de columna (las views filtran con
-- TRIM(col); un índice plano no se usaría, uno sobre TRIM(col) sí). MySQL 8.0.13+.
CREATE INDEX idx_cp_t_accion
    ON cp_tbl_mov_completo_29_05_26 ((TRIM(accion_nombre)));
CREATE INDEX idx_cp_t_motivo
    ON cp_tbl_mov_completo_29_05_26 ((TRIM(motivo_nombre)));

-- Filtros/orden frecuentes adicionales (descomentar según uso real):
-- CREATE INDEX idx_cptbl_posicion   ON cp_tbl_mov_completo_29_05_26 (posicion);
-- CREATE INDEX idx_cptbl_numemp     ON cp_tbl_mov_completo_29_05_26 (num_empleado);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. OPCIONAL — Búsqueda de texto rápida en MOV_POS.
--    Hoy la búsqueda usa LIKE '%texto%' (icontains) sobre varias columnas, lo
--    que provoca full table scan. Un índice FULLTEXT permite MATCH ... AGAINST
--    (muchísimo más rápido), PERO cambia la semántica: busca por PALABRAS, no
--    por subcadenas. Si se adopta, el endpoint debe usar MATCH(...) AGAINST(...)
--    en lugar de icontains.
--
-- ALTER TABLE MOV_POS ADD FULLTEXT INDEX ft_movpos_busqueda
--     (no_pos_actual, motivo, unidad_de_negocio, unidad_adva, puesto_ptal, descr, nombre_puesto);
