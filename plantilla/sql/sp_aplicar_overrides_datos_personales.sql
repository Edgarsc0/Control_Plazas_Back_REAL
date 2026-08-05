-- Reaplica los overrides activos de CeldaOverride (tabla='DATOS_PERSONALES')
-- sobre DATOS_PERSONALES, en el servidor (1 UPDATE...JOIN por columna
-- distinta, en vez de traer filas a Python y hacer bulk_update). Reemplaza
-- la lógica de `plantilla.celda_override.aplicar_overrides_datos_personales`.
--
-- Por qué: esa función corre contra una BD remota (alta latencia WAN); cada
-- vuelta Python<->MySQL cuesta cara. Aquí todo el trabajo (join override -> fila
-- viva vía no_empleado, 1 UPDATE por columna) ocurre dentro de MySQL, sin
-- round-trips extra.
--
-- MANTENIMIENTO: el mapeo de columna (nombre de campo Django en
-- CeldaOverride.columna) -> columna real de DATOS_PERSONALES está hardcodeado
-- en el CASE de abajo, a propósito, como whitelist (una columna que no matchea
-- ningún WHEN se ignora, no llega a SQL dinámico). Si se agrega/quita una
-- columna editable en EDITABLE_COLUMNS_DATOS_PERSONALES (celda_override.py),
-- hay que actualizar este CASE también.
--
-- Ejecutar manualmente en MySQL:
--   mysql -u <user> -p <db> < plantilla/sql/sp_aplicar_overrides_datos_personales.sql

DROP PROCEDURE IF EXISTS sp_aplicar_overrides_datos_personales;

DELIMITER $$

CREATE PROCEDURE sp_aplicar_overrides_datos_personales(
    OUT p_aplicados INT,
    OUT p_huerfanos INT
)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_columna VARCHAR(128);
    DECLARE v_real_columna VARCHAR(128);
    DECLARE v_total INT;
    DECLARE cur CURSOR FOR
        SELECT DISTINCT columna
        FROM plantilla_celdaoverride
        WHERE tabla = 'DATOS_PERSONALES' AND activo = 1;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    SELECT COUNT(*) INTO v_total
    FROM plantilla_celdaoverride
    WHERE tabla = 'DATOS_PERSONALES' AND activo = 1;

    SELECT COUNT(*) INTO p_huerfanos
    FROM plantilla_celdaoverride ov
    LEFT JOIN DATOS_PERSONALES dp
        ON JSON_UNQUOTE(JSON_EXTRACT(ov.clave_negocio, '$.no_empleado')) = dp.NO_EMPLEADO
    WHERE ov.tabla = 'DATOS_PERSONALES' AND ov.activo = 1 AND dp.id IS NULL;

    SET p_aplicados = v_total - p_huerfanos;

    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_columna;
        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Whitelist: python attname (CeldaOverride.columna) -> columna real
        -- DATOS_PERSONALES. Debe reflejar EDITABLE_COLUMNS_DATOS_PERSONALES.
        SET v_real_columna = CASE v_columna
            WHEN 'escolaridad_tipo'     THEN 'ESCOLARIDAD_TIPO'
            WHEN 'escolaridad_nivrl'    THEN 'ESCOLARIDAD_NIVRL'
            WHEN 'escolaridad_area'     THEN 'ESCOLARIDAD_AREA'
            WHEN 'carrera'              THEN 'CARRERA'
            WHEN 'centro_escolar'       THEN 'CENTRO_ESCOLAR'
            WHEN 'phone'                THEN 'PHONE'
            WHEN 'phone1'               THEN 'PHONE1'
            WHEN 'extension'            THEN 'extension'
            WHEN 'conmutador'           THEN 'Conmutador'
            WHEN 'email_addr'           THEN 'EMAIL_ADDR'
            WHEN 'email_addr2'          THEN 'EMAIL_ADDR2'
            WHEN 'calle'                THEN 'CALLE'
            WHEN 'hr_numero_exterior'   THEN 'HR_NUMERO_EXTERIOR'
            WHEN 'hr_numero_interior'   THEN 'HR_NUMERO_INTERIOR'
            WHEN 'colonia'              THEN 'COLONIA'
            WHEN 'postal'               THEN 'POSTAL'
            WHEN 'hr_municipio'         THEN 'HR_MUNICIPIO'
            WHEN 'estado'               THEN 'ESTADO'
            ELSE NULL
        END;

        IF v_real_columna IS NOT NULL THEN
            IF v_columna = 'extension' THEN
                -- valor_nuevo llega serializado (json.dumps) desde Python;
                -- se aplica nativo sobre la columna JSON viva.
                SET @sql = CONCAT(
                    'UPDATE DATOS_PERSONALES dp JOIN plantilla_celdaoverride ov ',
                    'ON JSON_UNQUOTE(JSON_EXTRACT(ov.clave_negocio, ''$.no_empleado'')) = dp.NO_EMPLEADO ',
                    'SET dp.`', v_real_columna, '` = CAST(ov.valor_nuevo AS JSON) ',
                    'WHERE ov.tabla = ''DATOS_PERSONALES'' AND ov.activo = 1 AND ov.columna = ''', v_columna, ''''
                );
            ELSE
                SET @sql = CONCAT(
                    'UPDATE DATOS_PERSONALES dp JOIN plantilla_celdaoverride ov ',
                    'ON JSON_UNQUOTE(JSON_EXTRACT(ov.clave_negocio, ''$.no_empleado'')) = dp.NO_EMPLEADO ',
                    'SET dp.`', v_real_columna, '` = ov.valor_nuevo ',
                    'WHERE ov.tabla = ''DATOS_PERSONALES'' AND ov.activo = 1 AND ov.columna = ''', v_columna, ''''
                );
            END IF;

            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
        END IF;
    END LOOP;
    CLOSE cur;
END$$

DELIMITER ;
