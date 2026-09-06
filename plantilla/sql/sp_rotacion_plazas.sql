-- =============================================================================
-- sp_rotacion_plazas()
--
-- Version SET-BASED de sp_historia_plaza aplicada a TODAS las plazas de una
-- sola pasada (~30-40s para 12,693 plazas / 156k movimientos), materializada en
-- dos tablas:
--
--   rotacion_plaza_periodo   la pila cronologica continua de cada plaza; mismas
--                            columnas que devuelve sp_historia_plaza, mas
--                            `posicion`. Alimenta el swimlane (vista principal).
--   rotacion_plaza_metrica   una fila por plaza con sus metricas de rotacion y
--                            sus descriptores actuales (SIG). Alimenta la tabla
--                            de entrada, que es donde el usuario ordena y filtra
--                            para decidir que plazas mirar en el swimlane.
--   rotacion_plaza_meta      una sola fila: cuando se reconstruyo y con que
--                            volumenes, para que la UI pueda decir "datos al X".
--
-- POR QUE MATERIALIZAR: sp_historia_plaza resuelve UNA plaza (~30ms). Pedir
-- 12,693 plazas por request son ~6 minutos; y tanto la tabla de metricas como
-- el swimlane necesitan el universo completo para ordenar y filtrar. El calculo
-- corre una vez por carga del ETL (comando `reconstruir_rotacion_plazas`) y los
-- endpoints quedan como SELECT planos.
--
-- EQUIVALENCIA CON sp_historia_plaza: validado 2026-09-05 contra el SP fila por
-- fila en 200 plazas (muestra estratificada: 60 con mas movimientos y/o
-- insubsistencias + 140 al azar) -> 1,068 filas, 0 diferencias en orden,
-- tipo_periodo, num_gestion, num_empleado, fechas, dias, tipo_cierre,
-- posicion_destino, es_ocupante_actual e inconsistente.
--
-- Cualquier cambio de reglas en sp_historia_plaza debe replicarse aqui. Las
-- diferencias estructurales frente a aquel son solo dos, ambas obligadas por
-- procesar todas las plazas juntas:
--   1. Toda ventana lleva PARTITION BY posicion.
--   2. Donde el SP original usa una subconsulta correlacionada o un
--      "UPDATE ... ORDER BY ... LIMIT 1" (que resuelven una plaza a la vez),
--      aqui va un JOIN agregado o un ROW_NUMBER().
-- Se usan TEMPORARY TABLES duplicadas (tmp_base / tmp_base_b) porque MySQL no
-- permite referenciar la misma temporary table dos veces en una sentencia
-- ("Can't reopen table").
--
-- AVISO: los id de cp_tbl_mov_completo_29_05_26 NO son estables entre cargas
-- del ETL. Se materializan aqui solo como referencia al momento del calculo.
-- =============================================================================

CREATE TABLE IF NOT EXISTS rotacion_plaza_periodo (
    id                 BIGINT AUTO_INCREMENT PRIMARY KEY,
    posicion           VARCHAR(50)  NOT NULL,
    orden              INT          NOT NULL,
    tipo_periodo       VARCHAR(16)  NOT NULL,
    num_gestion        INT          NULL,
    num_empleado       VARCHAR(20)  NOT NULL DEFAULT '',
    nombre_completo    VARCHAR(200) NOT NULL DEFAULT '',
    fecha_inicio       DATE         NULL,
    fecha_fin          DATE         NULL,
    dias               INT          NULL,
    id_registro_inicio BIGINT       NULL,
    fuente_id_inicio   VARCHAR(16)  NULL,
    id_registro_fin    BIGINT       NULL,
    accion_entrada     VARCHAR(100) NULL,
    motivo_entrada     VARCHAR(100) NULL,
    accion_salida      VARCHAR(100) NULL,
    motivo_salida      VARCHAR(100) NULL,
    tipo_cierre        VARCHAR(16)  NULL,
    posicion_destino   VARCHAR(50)  NULL,
    es_ocupante_actual TINYINT      NOT NULL DEFAULT 0,
    inconsistente      TINYINT      NOT NULL DEFAULT 0,
    nivel_entrada      VARCHAR(50)  NULL,
    nivel_salida       VARCHAR(50)  NULL,
    UNIQUE KEY uq_pos_orden (posicion, orden),
    KEY ix_periodo_emp (num_empleado),
    KEY ix_periodo_tipo (tipo_periodo),
    KEY ix_periodo_fechas (fecha_inicio, fecha_fin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rotacion_plaza_metrica (
    posicion                VARCHAR(50) PRIMARY KEY,
    -- Estado actual
    ocupada                 TINYINT      NOT NULL DEFAULT 0,
    num_empleado_actual     VARCHAR(20)  NULL,
    nombre_actual           VARCHAR(200) NULL,
    dias_en_estado_actual   INT          NULL,
    -- Linea de tiempo
    fecha_creacion          DATE         NULL,
    fecha_primer_movimiento DATE         NULL,
    fecha_ultimo_movimiento DATE         NULL,
    dias_desde_creacion     INT          NULL,
    -- Conteos
    num_gestiones           INT NOT NULL DEFAULT 0,
    num_ocupantes_distintos INT NOT NULL DEFAULT 0,
    num_insubsistencias     INT NOT NULL DEFAULT 0,
    num_transitos           INT NOT NULL DEFAULT 0,
    num_vacancias           INT NOT NULL DEFAULT 0,
    num_salidas_traslado    INT NOT NULL DEFAULT 0,
    num_salidas_baja        INT NOT NULL DEFAULT 0,
    num_periodos_inconsistentes INT NOT NULL DEFAULT 0,
    -- Tiempos
    dias_ocupada            INT NOT NULL DEFAULT 0,
    dias_vacante            INT NOT NULL DEFAULT 0,
    pct_vacante             DECIMAL(6,2) NULL,
    -- Duracion de las gestiones CERRADAS (las abiertas estan censuradas: la
    -- gestion en curso todavia no sabe cuanto va a durar, meterla en el
    -- promedio lo sesga hacia abajo). La vigente va aparte, en
    -- dias_en_estado_actual.
    gestion_dias_min        INT NULL,
    gestion_dias_max        INT NULL,
    gestion_dias_prom       DECIMAL(10,1) NULL,
    gestion_dias_mediana    DECIMAL(10,1) NULL,
    -- Metrica de cabecera de la tabla de entrada: cuantas gestiones por año ha
    -- consumido la plaza desde que existe. Es el numero por el que se ordena
    -- para responder "cuales plazas rotan mas".
    gestiones_por_anio      DECIMAL(8,3) NULL,
    -- Descriptores actuales (EMPLEADOS_COMPLETOS_SIG)
    aduana                  VARCHAR(255) NULL,
    unidad_administrativa   VARCHAR(255) NULL,
    puesto                  VARCHAR(255) NULL,
    nivel                   VARCHAR(255) NULL,
    ubicacion               VARCHAR(255) NULL,
    entidad_federativa      VARCHAR(255) NULL,
    nj                      VARCHAR(255) NULL,
    tipo_contratacion       VARCHAR(255) NULL,
    personal_militar_civil  VARCHAR(255) NULL,
    rango                   VARCHAR(255) NULL,
    KEY ix_met_rot (gestiones_por_anio),
    KEY ix_met_gest (num_gestiones),
    KEY ix_met_aduana (aduana),
    KEY ix_met_ua (unidad_administrativa),
    KEY ix_met_ocupada (ocupada)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rotacion_plaza_meta (
    id              TINYINT PRIMARY KEY,
    calculado_en    DATETIME NOT NULL,
    segundos        INT      NULL,
    num_plazas      INT      NOT NULL DEFAULT 0,
    num_periodos    INT      NOT NULL DEFAULT 0,
    fuente          VARCHAR(100) NOT NULL DEFAULT 'cp_tbl_mov_completo_29_05_26'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP PROCEDURE IF EXISTS sp_rotacion_plazas;

DELIMITER $$

CREATE PROCEDURE sp_rotacion_plazas()
BEGIN
    DECLARE v_ini DATETIME DEFAULT NOW();

    -- READ COMMITTED: la pasada lee EMPLEADOS_COMPLETOS_SIG y MOV_POS, que
    -- tienen escritores concurrentes (ETL). Con REPEATABLE READ esta lectura
    -- larga llega a chocar con ellos ("Deadlock found when trying to get lock").
    SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

    -- =========================================================================
    -- 1. Base de movimientos + copia gemela.
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_base;
    CREATE TEMPORARY TABLE tmp_base (
        id BIGINT, posicion VARCHAR(50), emp VARCHAR(20), accion VARCHAR(50),
        accion_nombre VARCHAR(100), motivo_nombre VARCHAR(100),
        fecha_efectiva DATE, sec INT, fecha_captura DATE,
        PRIMARY KEY (id), KEY (posicion, fecha_efectiva), KEY (emp, fecha_efectiva, sec)
    ) ENGINE=InnoDB
    SELECT id, posicion,
           TRIM(COALESCE(num_empleado, '')) AS emp,
           accion, COALESCE(accion_nombre, '') AS accion_nombre,
           COALESCE(motivo_nombre, '') AS motivo_nombre,
           fecha_efectiva, COALESCE(sec, 0) AS sec, fecha_captura
    FROM cp_tbl_mov_completo_29_05_26
    WHERE fecha_efectiva IS NOT NULL;

    DROP TEMPORARY TABLE IF EXISTS tmp_base_b;
    CREATE TEMPORARY TABLE tmp_base_b (
        id BIGINT, posicion VARCHAR(50), emp VARCHAR(20),
        fecha_efectiva DATE, sec INT, fecha_captura DATE,
        accion VARCHAR(50), accion_nombre VARCHAR(100), motivo_nombre VARCHAR(100),
        PRIMARY KEY (id), KEY (posicion, fecha_efectiva), KEY (emp, fecha_efectiva, sec)
    ) ENGINE=InnoDB
    SELECT id, posicion, emp, fecha_efectiva, sec, fecha_captura,
           accion, accion_nombre, motivo_nombre
    FROM tmp_base;

    -- =========================================================================
    -- 2. Spells por (posicion, empleado) -- Regla 1 de sp_historia_plaza.
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_sig;
    CREATE TEMPORARY TABLE tmp_sig (
        id BIGINT PRIMARY KEY, sig_accion_emp VARCHAR(50), sig_fecha_emp DATE
    ) ENGINE=InnoDB
    SELECT id,
           LEAD(accion)         OVER w AS sig_accion_emp,
           LEAD(fecha_efectiva) OVER w AS sig_fecha_emp
    FROM tmp_base
    WINDOW w AS (PARTITION BY posicion, emp ORDER BY fecha_efectiva, sec, id);

    -- `cierra`: (a) baja que no es renovacion tecnica -- Regla 2; (b) otro
    -- empleado toco la plaza entre esta fila y el proximo movimiento de este
    -- mismo empleado. En sp_historia_plaza (b) es un EXISTS correlacionado
    -- contra la unica plaza en juego; aqui es un LEFT JOIN + MAX, que resuelve
    -- lo mismo para las 12,693 de un golpe.
    DROP TEMPORARY TABLE IF EXISTS tmp_cierra;
    CREATE TEMPORARY TABLE tmp_cierra (id BIGINT PRIMARY KEY, cierra TINYINT) ENGINE=InnoDB
    SELECT b.id,
           MAX(CASE
             WHEN b.accion IN ('TER', 'TE1')
                  AND NOT (s.sig_accion_emp IN ('RE1', 'REH')
                           AND s.sig_fecha_emp = b.fecha_efectiva
                           AND b.motivo_nombre NOT IN ('Insubsistencia Nombramiento*',
                                                       'Insubsistencia Contrato HH'))
             THEN 1
             WHEN o.id IS NOT NULL THEN 1
             ELSE 0
           END) AS cierra
    FROM tmp_base b
    JOIN tmp_sig s ON s.id = b.id
    LEFT JOIN tmp_base_b o
           ON o.posicion = b.posicion
          AND o.emp <> b.emp
          AND o.fecha_efectiva > b.fecha_efectiva
          AND (s.sig_fecha_emp IS NULL OR o.fecha_efectiva < s.sig_fecha_emp)
    GROUP BY b.id;

    DROP TEMPORARY TABLE IF EXISTS tmp_spells;
    CREATE TEMPORARY TABLE tmp_spells (
        posicion VARCHAR(50), emp VARCHAR(20), sp_id INT,
        f_ini DATE, f_fin DATE, id_ini BIGINT, id_fin BIGINT,
        acc_ini VARCHAR(50), acc_ini_nom VARCHAR(100), mot_ini VARCHAR(100),
        acc_fin VARCHAR(50), acc_fin_nom VARCHAR(100), mot_fin VARCHAR(100),
        fin_es_baja TINYINT, fin_fecha_mov DATE, fin_sec INT,
        es_insub TINYINT, es_solapada TINYINT DEFAULT 0,
        tipo_cierre VARCHAR(16), pos_destino VARCHAR(50),
        inconsistente TINYINT DEFAULT 0, orden INT,
        PRIMARY KEY (posicion, emp, sp_id),
        KEY (posicion, orden), KEY (emp), KEY (f_ini)
    ) ENGINE=InnoDB
    SELECT posicion, emp, sp_id,
           MAX(CASE WHEN rn_asc  = 1 THEN fecha_efectiva END) AS f_ini,
           CAST(NULL AS DATE)                                 AS f_fin,
           MAX(CASE WHEN rn_asc  = 1 THEN id END)             AS id_ini,
           MAX(CASE WHEN rn_desc = 1 THEN id END)             AS id_fin,
           MAX(CASE WHEN rn_asc  = 1 THEN accion END)         AS acc_ini,
           MAX(CASE WHEN rn_asc  = 1 THEN accion_nombre END)  AS acc_ini_nom,
           MAX(CASE WHEN rn_asc  = 1 THEN motivo_nombre END)  AS mot_ini,
           MAX(CASE WHEN rn_desc = 1 THEN accion END)         AS acc_fin,
           MAX(CASE WHEN rn_desc = 1 THEN accion_nombre END)  AS acc_fin_nom,
           MAX(CASE WHEN rn_desc = 1 THEN motivo_nombre END)  AS mot_fin,
           MAX(CASE WHEN rn_desc = 1 AND accion IN ('TER','TE1') THEN 1 ELSE 0 END) AS fin_es_baja,
           MAX(CASE WHEN rn_desc = 1 THEN fecha_efectiva END) AS fin_fecha_mov,
           MAX(CASE WHEN rn_desc = 1 THEN sec END)            AS fin_sec,
           MAX(CASE WHEN motivo_nombre IN ('Insubsistencia Nombramiento*',
                                           'Insubsistencia Contrato HH') THEN 1 ELSE 0 END) AS es_insub,
           0 AS es_solapada,
           CAST(NULL AS CHAR(16)) AS tipo_cierre,
           CAST(NULL AS CHAR(50)) AS pos_destino,
           0 AS inconsistente,
           0 AS orden
    FROM (
        SELECT c.*,
               ROW_NUMBER() OVER (PARTITION BY posicion, emp, sp_id
                                  ORDER BY fecha_efectiva ASC,  sec ASC,  id ASC)  AS rn_asc,
               ROW_NUMBER() OVER (PARTITION BY posicion, emp, sp_id
                                  ORDER BY fecha_efectiva DESC, sec DESC, id DESC) AS rn_desc
        FROM (
            SELECT b.*,
                   COALESCE(SUM(k.cierra) OVER (PARTITION BY b.posicion, b.emp
                                                ORDER BY b.fecha_efectiva, b.sec, b.id
                                                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS sp_id
            FROM tmp_base b JOIN tmp_cierra k ON k.id = b.id
        ) c
    ) n
    GROUP BY posicion, emp, sp_id;

    -- =========================================================================
    -- 3. Cierre de cada tramo: baja directa o traslado a otra posicion.
    -- =========================================================================
    UPDATE tmp_spells
    SET f_fin = fin_fecha_mov, tipo_cierre = 'baja'
    WHERE fin_es_baja = 1;

    -- Traslado (Regla 3): primer movimiento posterior del empleado en OTRA
    -- posicion. El original lo resuelve con una subconsulta correlacionada por
    -- tramo; aqui se agrega con el truco de codificar la llave de orden y el id
    -- en un string y quedarse con el MIN -- un solo JOIN para todos los tramos.
    DROP TEMPORARY TABLE IF EXISTS tmp_tras;
    CREATE TEMPORARY TABLE tmp_tras (
        posicion VARCHAR(50), emp VARCHAR(20), sp_id INT, id_tras BIGINT,
        PRIMARY KEY (posicion, emp, sp_id)
    ) ENGINE=InnoDB
    SELECT s.posicion, s.emp, s.sp_id,
           CAST(SUBSTRING_INDEX(
               MIN(CONCAT(t.fecha_efectiva, '|', LPAD(t.sec, 6, '0'), '|',
                          COALESCE(t.fecha_captura, '9999-12-31'), '|', LPAD(t.id, 12, '0'))),
               '|', -1) AS UNSIGNED) AS id_tras
    FROM tmp_spells s
    JOIN tmp_base_b t
      ON t.emp = s.emp
     AND t.posicion <> s.posicion
     AND (t.fecha_efectiva > s.fin_fecha_mov
          OR (t.fecha_efectiva = s.fin_fecha_mov AND t.sec > s.fin_sec))
    WHERE s.fin_es_baja = 0 AND s.emp <> ''
    GROUP BY s.posicion, s.emp, s.sp_id;

    UPDATE tmp_spells s
      JOIN tmp_tras x ON x.posicion = s.posicion AND x.emp = s.emp AND x.sp_id = s.sp_id
      JOIN tmp_base t ON t.id = x.id_tras
    SET s.f_fin       = t.fecha_efectiva,
        s.id_fin      = t.id,
        s.pos_destino = t.posicion,
        s.acc_fin     = t.accion,
        s.acc_fin_nom = COALESCE(t.accion_nombre, ''),
        s.mot_fin     = COALESCE(t.motivo_nombre, ''),
        s.tipo_cierre = 'traslado';

    UPDATE tmp_spells SET tipo_cierre = 'actual', f_fin = NULL
    WHERE tipo_cierre IS NULL OR (tipo_cierre = 'traslado' AND f_fin IS NULL);

    -- es_solapada: insubsistencia cuya fecha cae DENTRO de una ocupacion real
    -- vigente (nombramiento sobre plaza ya ocupada) -> anuncio lateral, no
    -- participa en la cadena.
    DROP TEMPORARY TABLE IF EXISTS tmp_reales;
    CREATE TEMPORARY TABLE tmp_reales (
        posicion VARCHAR(50), f_ini DATE, f_fin DATE, KEY (posicion, f_ini)
    ) ENGINE=InnoDB
    SELECT posicion, f_ini, f_fin FROM tmp_spells WHERE es_insub = 0;

    UPDATE tmp_spells s
    SET s.es_solapada = 1
    WHERE s.es_insub = 1
      AND EXISTS (
          SELECT 1 FROM tmp_reales r
          WHERE r.posicion = s.posicion
            AND r.f_ini <= s.f_ini AND (r.f_fin IS NULL OR r.f_fin > s.f_ini)
      );

    -- =========================================================================
    -- 4. Orden cronologico de los tramos DENTRO de cada plaza.
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_orden;
    CREATE TEMPORARY TABLE tmp_orden (
        posicion VARCHAR(50), emp VARCHAR(20), sp_id INT, n INT,
        PRIMARY KEY (posicion, emp, sp_id)
    ) ENGINE=InnoDB
    SELECT posicion, emp, sp_id,
           ROW_NUMBER() OVER (PARTITION BY posicion ORDER BY f_ini, id_ini) AS n
    FROM tmp_spells;

    UPDATE tmp_spells s
      JOIN tmp_orden o ON o.posicion = s.posicion AND o.emp = s.emp AND o.sp_id = s.sp_id
    SET s.orden = o.n;

    -- =========================================================================
    -- 5. Clamp: el fin de un tramo no puede exceder el inicio del siguiente.
    --
    -- GUARD `orden = MAX(orden) OVER (PARTITION BY posicion)`: MySQL 8.0.46
    -- devuelve la propia fila en un frame ROWS ... AND 1 PRECEDING cuando la
    -- particion trae una sola fila, en vez del frame vacio del estandar. Sin el
    -- guard, una plaza de un unico tramo se recorta contra si misma y su
    -- gestion colapsa a 0 dias. Mismo defecto y mismo guard que
    -- sp_historia_plaza.sql (ver la nota larga alli).
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_next;
    CREATE TEMPORARY TABLE tmp_next (
        posicion VARCHAR(50), orden INT, sig_f_ini_real DATE,
        PRIMARY KEY (posicion, orden)
    ) ENGINE=InnoDB
    SELECT posicion, orden,
           CASE WHEN orden = MAX(orden) OVER (PARTITION BY posicion) THEN NULL ELSE
               CAST(SUBSTRING_INDEX(
                   MIN(CASE WHEN NOT (es_insub = 1 AND es_solapada = 1)
                            THEN CONCAT(LPAD(orden, 10, '0'), '|', f_ini) END)
                       OVER (PARTITION BY posicion ORDER BY orden DESC
                             ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),
                   '|', -1) AS DATE)
           END AS sig_f_ini_real
    FROM tmp_spells;

    UPDATE tmp_spells s
    JOIN tmp_next n ON n.posicion = s.posicion AND n.orden = s.orden
    SET s.f_fin = n.sig_f_ini_real, s.tipo_cierre = 'clamp', s.inconsistente = 1
    WHERE n.sig_f_ini_real IS NOT NULL
      AND (s.f_fin IS NULL OR s.f_fin > n.sig_f_ini_real);

    -- =========================================================================
    -- 6. El ocupante actual segun SIG manda: se reabre su ultimo tramo real.
    --    (El original hace "UPDATE ... ORDER BY orden DESC LIMIT 1" por plaza;
    --    aqui el mismo criterio se expresa con ROW_NUMBER.)
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_sig_actual;
    CREATE TEMPORARY TABLE tmp_sig_actual (
        posicion VARCHAR(50) PRIMARY KEY, emp VARCHAR(20), ocupada TINYINT
    ) ENGINE=InnoDB
    SELECT TRIM(`Posición`) AS posicion,
           TRIM(COALESCE(Numempleado, '')) AS emp,
           CASE WHEN TRIM(COALESCE(`Estado Nómina`, '')) <> '' THEN 1 ELSE 0 END AS ocupada
    FROM EMPLEADOS_COMPLETOS_SIG
    WHERE TRIM(COALESCE(`Posición`, '')) <> '';

    DROP TEMPORARY TABLE IF EXISTS tmp_reabrir;
    CREATE TEMPORARY TABLE tmp_reabrir (
        posicion VARCHAR(50), emp VARCHAR(20), sp_id INT,
        PRIMARY KEY (posicion, emp, sp_id)
    ) ENGINE=InnoDB
    SELECT posicion, emp, sp_id FROM (
        SELECT s.posicion, s.emp, s.sp_id,
               ROW_NUMBER() OVER (PARTITION BY s.posicion ORDER BY s.orden DESC) AS rn
        FROM tmp_spells s
        JOIN tmp_sig_actual a
          ON a.posicion = s.posicion AND a.emp = s.emp AND a.ocupada = 1 AND a.emp <> ''
        WHERE s.es_insub = 0
    ) z WHERE rn = 1;

    UPDATE tmp_spells s
    JOIN tmp_reabrir r ON r.posicion = s.posicion AND r.emp = s.emp AND r.sp_id = s.sp_id
    SET s.f_fin = NULL, s.tipo_cierre = 'actual', s.pos_destino = NULL;

    -- =========================================================================
    -- 7. Pila continua por plaza: creacion + tramos + vacancias intercaladas.
    -- =========================================================================
    DROP TEMPORARY TABLE IF EXISTS tmp_crea;
    CREATE TEMPORARY TABLE tmp_crea (
        posicion VARCHAR(50) PRIMARY KEY, crea_fecha DATE, crea_id BIGINT
    ) ENGINE=InnoDB
    SELECT posicion,
           CAST(SUBSTRING_INDEX(clave, '|', 1) AS DATE) AS crea_fecha,
           CAST(SUBSTRING_INDEX(clave, '|', -1) AS UNSIGNED) AS crea_id
    FROM (
        SELECT TRIM(`Nº Pos Actual`) AS posicion,
               MIN(CONCAT(`F Efva`, '|', COALESCE(`Fecha Captura`, '9999-12-31'),
                          '|', LPAD(id, 12, '0'))) AS clave
        FROM MOV_POS
        WHERE TRIM(COALESCE(`Nº Pos Actual`, '')) <> ''
          AND STR_TO_DATE(`F Efva`, '%Y-%m-%d') IS NOT NULL
        GROUP BY 1
    ) z;

    -- Mismo GUARD que el paso 5.
    DROP TEMPORARY TABLE IF EXISTS tmp_next2;
    CREATE TEMPORARY TABLE tmp_next2 (
        posicion VARCHAR(50), orden INT, f_ini DATE, f_fin DATE, id_ini BIGINT,
        emp VARCHAR(20), es_insub TINYINT, es_solapada TINYINT,
        sig_f_ini_real DATE, sig_id_ini_real BIGINT,
        PRIMARY KEY (posicion, orden)
    ) ENGINE=InnoDB
    SELECT posicion, orden, f_ini, f_fin, id_ini, emp, es_insub, es_solapada,
           CASE WHEN es_ultimo = 1 THEN NULL
                ELSE CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(sig, '|', 2), '|', -1) AS DATE) END
               AS sig_f_ini_real,
           CASE WHEN es_ultimo = 1 THEN NULL
                ELSE CAST(SUBSTRING_INDEX(sig, '|', -1) AS UNSIGNED) END
               AS sig_id_ini_real
    FROM (
        SELECT posicion, orden, f_ini, f_fin, id_ini, emp, es_insub, es_solapada,
               CASE WHEN orden = MAX(orden) OVER (PARTITION BY posicion) THEN 1 ELSE 0 END AS es_ultimo,
               MIN(CASE WHEN NOT (es_insub = 1 AND es_solapada = 1)
                        THEN CONCAT(LPAD(orden, 10, '0'), '|', f_ini, '|', id_ini) END)
                   OVER (PARTITION BY posicion ORDER BY orden DESC
                         ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS sig
        FROM tmp_spells
    ) z;

    DROP TEMPORARY TABLE IF EXISTS tmp_primero;
    CREATE TEMPORARY TABLE tmp_primero (
        posicion VARCHAR(50) PRIMARY KEY, f_ini DATE, id_ini BIGINT
    ) ENGINE=InnoDB
    SELECT posicion, f_ini, id_ini FROM tmp_next2 WHERE orden = 1;

    DROP TEMPORARY TABLE IF EXISTS tmp_resumen;
    CREATE TEMPORARY TABLE tmp_resumen (
        posicion VARCHAR(50) PRIMARY KEY, max_f_fin DATE, abiertos INT, min_f_ini DATE
    ) ENGINE=InnoDB
    SELECT posicion, MAX(f_fin) AS max_f_fin,
           COUNT(CASE WHEN f_fin IS NULL THEN 1 END) AS abiertos,
           MIN(f_ini) AS min_f_ini
    FROM tmp_next2 GROUP BY posicion;

    DROP TEMPORARY TABLE IF EXISTS tmp_pila;
    CREATE TEMPORARY TABLE tmp_pila (
        posicion        VARCHAR(50),
        -- ord_sub desempata dentro de una misma fecha:
        --   0 creacion | 1 vacancia inicial y tramos | 2 vacancia intermedia | 3 vacancia final
        ord_fecha       DATE,
        ord_sub         INT,
        tipo_periodo    VARCHAR(16),
        num_empleado    VARCHAR(20),
        fecha_inicio    DATE,
        fecha_fin       DATE,
        id_registro_inicio BIGINT,
        fuente_id_inicio   VARCHAR(16),
        id_registro_fin    BIGINT,
        accion_entrada  VARCHAR(100),
        motivo_entrada  VARCHAR(100),
        accion_salida   VARCHAR(100),
        motivo_salida   VARCHAR(100),
        tipo_cierre     VARCHAR(16),
        posicion_destino VARCHAR(50),
        es_ocupante_actual TINYINT DEFAULT 0,
        inconsistente   TINYINT DEFAULT 0,
        KEY (posicion, ord_fecha, ord_sub)
    ) ENGINE=InnoDB;

    -- 7.a creacion
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, accion_entrada,
                          tipo_cierre, inconsistente)
    SELECT c.posicion, LEAST(c.crea_fecha, r.min_f_ini), 0, 'creacion', '',
           c.crea_fecha, c.crea_fecha, c.crea_id, 'MOV_POS', 'Nueva Posición', 'creacion',
           CASE WHEN c.crea_fecha > r.min_f_ini THEN 1 ELSE 0 END
    FROM tmp_crea c JOIN tmp_resumen r ON r.posicion = c.posicion
    WHERE c.crea_fecha IS NOT NULL;

    -- 7.b vacancia inicial (creacion -> primer nodo de la cadena)
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, id_registro_fin, tipo_cierre)
    SELECT c.posicion, c.crea_fecha, 1, 'vacancia', '', c.crea_fecha,
           p.f_ini, c.crea_id, 'MOV_POS', p.id_ini, 'ocupacion'
    FROM tmp_crea c JOIN tmp_primero p ON p.posicion = c.posicion
    WHERE c.crea_fecha IS NOT NULL AND p.f_ini > c.crea_fecha;

    -- 7.c tramos
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, id_registro_fin,
                          accion_entrada, motivo_entrada, accion_salida, motivo_salida,
                          tipo_cierre, posicion_destino, es_ocupante_actual, inconsistente)
    SELECT posicion, f_ini, 1,
           CASE WHEN es_insub = 1 THEN 'insubsistencia'
                WHEN f_fin IS NOT NULL AND f_fin = f_ini THEN 'transito'
                ELSE 'ocupacion' END,
           emp, f_ini, f_fin, id_ini, 'cp_tbl', id_fin,
           acc_ini_nom, mot_ini, COALESCE(acc_fin_nom, ''), COALESCE(mot_fin, ''),
           tipo_cierre, pos_destino,
           CASE WHEN tipo_cierre = 'actual' THEN 1 ELSE 0 END,
           inconsistente
    FROM tmp_spells;

    -- 7.d vacancias entre nodos (pila continua, sin huecos)
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, id_registro_fin, tipo_cierre)
    SELECT s.posicion, s.f_fin, 2, 'vacancia', '', s.f_fin, n.sig_f_ini_real,
           s.id_fin, 'cp_tbl', n.sig_id_ini_real, 'ocupacion'
    FROM tmp_spells s
    JOIN tmp_next2 n ON n.posicion = s.posicion AND n.orden = s.orden
    WHERE NOT (s.es_insub = 1 AND s.es_solapada = 1)
      AND s.f_fin IS NOT NULL
      AND n.sig_f_ini_real IS NOT NULL
      AND s.f_fin < n.sig_f_ini_real;

    -- 7.e vacancia final abierta
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, tipo_cierre)
    SELECT r.posicion, r.max_f_fin, 3, 'vacancia', '', r.max_f_fin, NULL, NULL, 'cp_tbl', 'vigente'
    FROM tmp_resumen r
    LEFT JOIN tmp_sig_actual a ON a.posicion = r.posicion
    WHERE COALESCE(a.ocupada, 0) = 0
      AND r.abiertos = 0
      AND r.max_f_fin IS NOT NULL;

    -- 7.f Plazas SIN un solo movimiento en cp_tbl (existen en MOV_POS y nunca
    --     fueron ocupadas): creacion + vacancia vigente. sp_historia_plaza las
    --     resuelve en su rama "IF (SELECT COUNT(*) FROM tmp_spells) = 0"; aqui
    --     son las que no aparecen en tmp_resumen.
    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, accion_entrada, tipo_cierre)
    SELECT c.posicion, c.crea_fecha, 0, 'creacion', '', c.crea_fecha, c.crea_fecha,
           c.crea_id, 'MOV_POS', 'Nueva Posición', 'creacion'
    FROM tmp_crea c
    LEFT JOIN tmp_resumen r ON r.posicion = c.posicion
    WHERE r.posicion IS NULL AND c.crea_fecha IS NOT NULL;

    INSERT INTO tmp_pila (posicion, ord_fecha, ord_sub, tipo_periodo, num_empleado, fecha_inicio,
                          fecha_fin, id_registro_inicio, fuente_id_inicio, tipo_cierre)
    SELECT c.posicion, c.crea_fecha, 1, 'vacancia', '', c.crea_fecha, NULL,
           c.crea_id, 'MOV_POS', 'vigente'
    FROM tmp_crea c
    LEFT JOIN tmp_resumen r ON r.posicion = c.posicion
    WHERE r.posicion IS NULL AND c.crea_fecha IS NOT NULL;

    -- =========================================================================
    -- 8. Materializacion de los periodos.
    -- =========================================================================
    -- nombre_completo por (posicion, empleado): un mismo empleado puede traer
    -- variantes del nombre entre movimientos, por eso GROUP BY + MAX y no
    -- DISTINCT (con DISTINCT el join duplicaba el periodo y partia la pila).
    DROP TEMPORARY TABLE IF EXISTS tmp_nombres;
    CREATE TEMPORARY TABLE tmp_nombres (
        posicion VARCHAR(50), num_empleado VARCHAR(20), nombre_completo VARCHAR(200),
        PRIMARY KEY (posicion, num_empleado)
    ) ENGINE=InnoDB
    SELECT posicion,
           TRIM(COALESCE(num_empleado, '')) AS num_empleado,
           MAX(TRIM(CONCAT(COALESCE(nombre, ''), ' ', COALESCE(ap_pat, ''), ' ',
                           COALESCE(ap_mat, '')))) AS nombre_completo
    FROM cp_tbl_mov_completo_29_05_26
    WHERE TRIM(COALESCE(num_empleado, '')) <> ''
    GROUP BY posicion, TRIM(COALESCE(num_empleado, ''));

    TRUNCATE TABLE rotacion_plaza_periodo;

    INSERT INTO rotacion_plaza_periodo
        (posicion, orden, tipo_periodo, num_gestion, num_empleado, nombre_completo,
         fecha_inicio, fecha_fin, dias, id_registro_inicio, fuente_id_inicio, id_registro_fin,
         accion_entrada, motivo_entrada, accion_salida, motivo_salida, tipo_cierre,
         posicion_destino, es_ocupante_actual, inconsistente, nivel_entrada, nivel_salida)
    SELECT p.posicion,
           ROW_NUMBER() OVER wp AS orden,
           p.tipo_periodo,
           CASE WHEN p.tipo_periodo = 'ocupacion'
                THEN ROW_NUMBER() OVER (PARTITION BY p.posicion, (p.tipo_periodo = 'ocupacion')
                                        ORDER BY p.ord_fecha, p.ord_sub,
                                                 CASE WHEN p.fecha_fin IS NOT NULL
                                                       AND p.fecha_fin = p.fecha_inicio
                                                      THEN 0 ELSE 1 END,
                                                 p.id_registro_inicio)
           END AS num_gestion,
           p.num_empleado,
           COALESCE(e.nombre_completo, '') AS nombre_completo,
           p.fecha_inicio, p.fecha_fin,
           -- Contratacion fechada a futuro: "dias transcurridos" no aplica -> 0.
           CASE WHEN p.fecha_fin IS NULL THEN GREATEST(DATEDIFF(CURDATE(), p.fecha_inicio), 0)
                ELSE DATEDIFF(p.fecha_fin, p.fecha_inicio) END AS dias,
           p.id_registro_inicio, p.fuente_id_inicio, p.id_registro_fin,
           p.accion_entrada, p.motivo_entrada, p.accion_salida, p.motivo_salida,
           p.tipo_cierre, p.posicion_destino, p.es_ocupante_actual, p.inconsistente,
           ni.nivel_tabular, nf.nivel_tabular
    FROM tmp_pila p
    LEFT JOIN tmp_nombres e
           ON e.posicion = p.posicion AND e.num_empleado = p.num_empleado AND p.num_empleado <> ''
    LEFT JOIN cp_tbl_mov_completo_29_05_26 ni
           ON ni.id = p.id_registro_inicio AND p.fuente_id_inicio = 'cp_tbl'
    LEFT JOIN cp_tbl_mov_completo_29_05_26 nf
           ON nf.id = p.id_registro_fin
    WINDOW wp AS (PARTITION BY p.posicion
                  ORDER BY p.ord_fecha, p.ord_sub,
                           -- un evento puntual (insubsistencia/transito) precede,
                           -- en la misma fecha, a un periodo que continua
                           CASE WHEN p.fecha_fin IS NOT NULL AND p.fecha_fin = p.fecha_inicio
                                THEN 0 ELSE 1 END,
                           p.id_registro_inicio);

    -- =========================================================================
    -- 9. Metricas por plaza.
    -- =========================================================================
    -- Mediana de las gestiones CERRADAS: promedio de la(s) fila(s) central(es)
    -- por posicion (MySQL no tiene PERCENTILE_CONT).
    DROP TEMPORARY TABLE IF EXISTS tmp_mediana;
    CREATE TEMPORARY TABLE tmp_mediana (
        posicion VARCHAR(50) PRIMARY KEY, mediana DECIMAL(10,1)
    ) ENGINE=InnoDB
    SELECT posicion, AVG(dias) AS mediana
    FROM (
        SELECT posicion, dias,
               ROW_NUMBER() OVER (PARTITION BY posicion ORDER BY dias) AS rn,
               COUNT(*)     OVER (PARTITION BY posicion)               AS c
        FROM rotacion_plaza_periodo
        WHERE tipo_periodo = 'ocupacion' AND fecha_fin IS NOT NULL
    ) z
    WHERE rn IN (FLOOR((c + 1) / 2), CEILING((c + 1) / 2))
    GROUP BY posicion;

    DROP TEMPORARY TABLE IF EXISTS tmp_agg;
    CREATE TEMPORARY TABLE tmp_agg (
        posicion VARCHAR(50) PRIMARY KEY,
        fecha_creacion DATE, fecha_primer_movimiento DATE, fecha_ultimo_movimiento DATE,
        num_gestiones INT, num_ocupantes_distintos INT, num_insubsistencias INT,
        num_transitos INT, num_vacancias INT, num_salidas_traslado INT,
        num_salidas_baja INT, num_periodos_inconsistentes INT,
        dias_ocupada INT, dias_vacante INT,
        gestion_dias_min INT, gestion_dias_max INT, gestion_dias_prom DECIMAL(10,1),
        num_empleado_actual VARCHAR(20), nombre_actual VARCHAR(200),
        dias_en_estado_actual INT
    ) ENGINE=InnoDB
    SELECT posicion,
           MIN(CASE WHEN tipo_periodo = 'creacion' THEN fecha_inicio END)         AS fecha_creacion,
           MIN(CASE WHEN tipo_periodo <> 'creacion' THEN fecha_inicio END)        AS fecha_primer_movimiento,
           MAX(CASE WHEN tipo_periodo <> 'creacion' THEN fecha_inicio END)        AS fecha_ultimo_movimiento,
           SUM(tipo_periodo = 'ocupacion')                                        AS num_gestiones,
           COUNT(DISTINCT CASE WHEN tipo_periodo = 'ocupacion' THEN num_empleado END) AS num_ocupantes_distintos,
           SUM(tipo_periodo = 'insubsistencia')                                   AS num_insubsistencias,
           SUM(tipo_periodo = 'transito')                                         AS num_transitos,
           SUM(tipo_periodo = 'vacancia')                                         AS num_vacancias,
           SUM(tipo_periodo = 'ocupacion' AND tipo_cierre = 'traslado')           AS num_salidas_traslado,
           SUM(tipo_periodo = 'ocupacion' AND tipo_cierre = 'baja')               AS num_salidas_baja,
           SUM(inconsistente)                                                     AS num_periodos_inconsistentes,
           COALESCE(SUM(CASE WHEN tipo_periodo = 'ocupacion' THEN dias END), 0)   AS dias_ocupada,
           COALESCE(SUM(CASE WHEN tipo_periodo = 'vacancia'  THEN dias END), 0)   AS dias_vacante,
           MIN(CASE WHEN tipo_periodo = 'ocupacion' AND fecha_fin IS NOT NULL THEN dias END) AS gestion_dias_min,
           MAX(CASE WHEN tipo_periodo = 'ocupacion' AND fecha_fin IS NOT NULL THEN dias END) AS gestion_dias_max,
           AVG(CASE WHEN tipo_periodo = 'ocupacion' AND fecha_fin IS NOT NULL THEN dias END) AS gestion_dias_prom,
           MAX(CASE WHEN es_ocupante_actual = 1 THEN num_empleado END)            AS num_empleado_actual,
           MAX(CASE WHEN es_ocupante_actual = 1 THEN nombre_completo END)         AS nombre_actual,
           -- El periodo vigente es el unico sin fecha_fin (ocupacion abierta o
           -- vacancia abierta): cuanto lleva la plaza como esta hoy.
           MAX(CASE WHEN fecha_fin IS NULL THEN dias END)                         AS dias_en_estado_actual
    FROM rotacion_plaza_periodo
    GROUP BY posicion;

    TRUNCATE TABLE rotacion_plaza_metrica;

    INSERT INTO rotacion_plaza_metrica
        (posicion, ocupada, num_empleado_actual, nombre_actual, dias_en_estado_actual,
         fecha_creacion, fecha_primer_movimiento, fecha_ultimo_movimiento, dias_desde_creacion,
         num_gestiones, num_ocupantes_distintos, num_insubsistencias, num_transitos,
         num_vacancias, num_salidas_traslado, num_salidas_baja, num_periodos_inconsistentes,
         dias_ocupada, dias_vacante, pct_vacante,
         gestion_dias_min, gestion_dias_max, gestion_dias_prom, gestion_dias_mediana,
         gestiones_por_anio,
         aduana, unidad_administrativa, puesto, nivel, ubicacion, entidad_federativa,
         nj, tipo_contratacion, personal_militar_civil, rango)
    SELECT a.posicion,
           CASE WHEN a.num_empleado_actual IS NOT NULL AND a.num_empleado_actual <> '' THEN 1 ELSE 0 END,
           a.num_empleado_actual, a.nombre_actual, a.dias_en_estado_actual,
           a.fecha_creacion, a.fecha_primer_movimiento, a.fecha_ultimo_movimiento,
           CASE WHEN a.fecha_creacion IS NOT NULL
                THEN GREATEST(DATEDIFF(CURDATE(), a.fecha_creacion), 0) END,
           a.num_gestiones, a.num_ocupantes_distintos, a.num_insubsistencias, a.num_transitos,
           a.num_vacancias, a.num_salidas_traslado, a.num_salidas_baja, a.num_periodos_inconsistentes,
           a.dias_ocupada, a.dias_vacante,
           CASE WHEN (a.dias_ocupada + a.dias_vacante) > 0
                THEN ROUND(100.0 * a.dias_vacante / (a.dias_ocupada + a.dias_vacante), 2) END,
           a.gestion_dias_min, a.gestion_dias_max, a.gestion_dias_prom, m.mediana,
           -- Se exige al menos un año de vida: con denominadores de dias sueltos
           -- una plaza creada la semana pasada y ocupada una vez daria "52
           -- gestiones por año" y encabezaria el orden sin significar nada.
           CASE WHEN a.fecha_creacion IS NOT NULL
                 AND DATEDIFF(CURDATE(), a.fecha_creacion) >= 365
                THEN ROUND(a.num_gestiones / (DATEDIFF(CURDATE(), a.fecha_creacion) / 365.25), 3) END,
           s.Aduana, s.`Unidad Administrativa`, s.`Nombre Puesto Funcional`, s.Nivel,
           s.`Ubicación`, s.`Entidad Federativa`, s.NJ, s.`TIPO DE CONTRATACIÓN`,
           s.`Personal Militar o Civil`, s.Rango
    FROM tmp_agg a
    LEFT JOIN tmp_mediana m ON m.posicion = a.posicion
    LEFT JOIN EMPLEADOS_COMPLETOS_SIG s ON TRIM(s.`Posición`) = a.posicion;

    -- =========================================================================
    -- 10. Sello de la corrida.
    -- =========================================================================
    DELETE FROM rotacion_plaza_meta;
    INSERT INTO rotacion_plaza_meta (id, calculado_en, segundos, num_plazas, num_periodos, fuente)
    SELECT 1, v_ini, TIMESTAMPDIFF(SECOND, v_ini, NOW()),
           (SELECT COUNT(*) FROM rotacion_plaza_metrica),
           (SELECT COUNT(*) FROM rotacion_plaza_periodo),
           'cp_tbl_mov_completo_29_05_26';

    DROP TEMPORARY TABLE IF EXISTS tmp_base;
    DROP TEMPORARY TABLE IF EXISTS tmp_base_b;
    DROP TEMPORARY TABLE IF EXISTS tmp_sig;
    DROP TEMPORARY TABLE IF EXISTS tmp_cierra;
    DROP TEMPORARY TABLE IF EXISTS tmp_spells;
    DROP TEMPORARY TABLE IF EXISTS tmp_tras;
    DROP TEMPORARY TABLE IF EXISTS tmp_reales;
    DROP TEMPORARY TABLE IF EXISTS tmp_orden;
    DROP TEMPORARY TABLE IF EXISTS tmp_next;
    DROP TEMPORARY TABLE IF EXISTS tmp_next2;
    DROP TEMPORARY TABLE IF EXISTS tmp_sig_actual;
    DROP TEMPORARY TABLE IF EXISTS tmp_reabrir;
    DROP TEMPORARY TABLE IF EXISTS tmp_crea;
    DROP TEMPORARY TABLE IF EXISTS tmp_primero;
    DROP TEMPORARY TABLE IF EXISTS tmp_resumen;
    DROP TEMPORARY TABLE IF EXISTS tmp_pila;
    DROP TEMPORARY TABLE IF EXISTS tmp_nombres;
    DROP TEMPORARY TABLE IF EXISTS tmp_mediana;
    DROP TEMPORARY TABLE IF EXISTS tmp_agg;
END$$

DELIMITER ;
