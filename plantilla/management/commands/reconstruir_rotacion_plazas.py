"""
Reconstruye las tablas materializadas de rotación de plazas.

    python manage.py reconstruir_rotacion_plazas

Llama a `sp_rotacion_plazas`, que rehace desde cero
`rotacion_plaza_periodo` (la pila cronológica de cada plaza) y
`rotacion_plaza_metrica` (una fila por plaza con sus métricas), y deja el sello
de la corrida en `rotacion_plaza_meta`.

CUÁNDO CORRERLO: después de cada carga del ETL que toque
cp_tbl_mov_completo_29_05_26, MOV_POS o EMPLEADOS_COMPLETOS_SIG. Los datos no
cambian solos; entre cargas la tabla materializada es válida indefinidamente.

Tarda ~21s sobre 156k movimientos / 13,254 plazas. Las tablas se llenan con
TRUNCATE + INSERT dentro del SP, así que el tab queda con datos incompletos
durante esos segundos — correrlo fuera de horario de uso.

Con --solo-desplegar sólo se (re)crea el procedimiento a partir del .sql, sin
recalcular: útil tras editar plantilla/sql/sp_rotacion_plazas.sql.
"""

import time
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import connection

SQL_PATH = Path(__file__).resolve().parents[2] / "sql" / "sp_rotacion_plazas.sql"

# Misma llave que usa RotacionPlazasMetricasView; si no se borra, el tab sigue
# sirviendo la foto anterior hasta que expire el TTL de 6 horas.
CACHE_METRICAS = "rotacion_plazas_metricas_v1"


class Command(BaseCommand):
    help = "Reconstruye rotacion_plaza_periodo y rotacion_plaza_metrica (sp_rotacion_plazas)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-desplegar",
            action="store_true",
            help="Sólo recrea el procedimiento desde el .sql, sin recalcular las tablas.",
        )
        parser.add_argument(
            "--sin-desplegar",
            action="store_true",
            help="Sólo recalcula; asume que el procedimiento ya está desplegado.",
        )

    def handle(self, *args, **opciones):
        if not opciones["sin_desplegar"]:
            self._desplegar()
        if opciones["solo_desplegar"]:
            return

        self.stdout.write("Reconstruyendo rotación de plazas…")
        inicio = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute("CALL sp_rotacion_plazas()")
            # El SP no devuelve resultsets, pero sí deja sets vacíos de los
            # CREATE ... SELECT: hay que agotarlos antes de reusar el cursor.
            while cursor.nextset():
                pass
            cursor.execute(
                "SELECT calculado_en, segundos, num_plazas, num_periodos "
                "FROM rotacion_plaza_meta WHERE id = 1"
            )
            fila = cursor.fetchone()

        cache.delete(CACHE_METRICAS)
        transcurrido = time.monotonic() - inicio

        if fila:
            calculado_en, segundos, num_plazas, num_periodos = fila
            self.stdout.write(
                self.style.SUCCESS(
                    f"Listo en {transcurrido:.1f}s (SP: {segundos}s) — "
                    f"{num_plazas:,} plazas, {num_periodos:,} periodos. "
                    f"Sello: {calculado_en}."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"El SP corrió ({transcurrido:.1f}s) pero rotacion_plaza_meta quedó vacía."
                )
            )

    def _desplegar(self):
        if not SQL_PATH.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró {SQL_PATH}"))
            return

        cuerpo = SQL_PATH.read_text(encoding="utf-8")
        # El .sql viene con DELIMITER $$ para poder llevar ';' dentro del cuerpo
        # del procedimiento. DELIMITER es una directiva del cliente mysql, no
        # SQL, así que el driver de Python no la entiende y hay que hacer aquí
        # el trabajo que haría ese cliente:
        #   1. Separar el archivo en la parte de DDL suelto (los CREATE TABLE y
        #      el DROP PROCEDURE) y el CREATE PROCEDURE ... END, que viaja como
        #      UNA sola sentencia.
        #   2. Quitar los comentarios ANTES de partir por ';'. Partir primero
        #      rompía el archivo a media prosa: el ';' de un comentario de la
        #      cabecera se tomaba como fin de sentencia.
        procedimiento = []
        preludio = []
        destino = preludio
        for linea in cuerpo.splitlines():
            desnuda = linea.strip()
            if desnuda.upper().startswith("DELIMITER"):
                continue
            if desnuda.upper().startswith("CREATE PROCEDURE"):
                destino = procedimiento
            if destino is procedimiento and desnuda == "END$$":
                procedimiento.append("END")
                destino = preludio
                continue
            destino.append(linea)

        sentencias = self._partir("\n".join(preludio))
        if procedimiento:
            sentencias.append("\n".join(procedimiento))

        with connection.cursor() as cursor:
            for sentencia in sentencias:
                limpia = sentencia.strip().rstrip(";").strip()
                if not limpia:
                    continue
                cursor.execute(limpia)
        self.stdout.write(self.style.SUCCESS("sp_rotacion_plazas desplegado."))

    @staticmethod
    def _partir(bloque):
        """Parte por ';' un bloque SIN cuerpo de procedimiento, ignorando comentarios."""
        sin_comentarios = "\n".join(
            linea
            for linea in bloque.splitlines()
            if linea.strip() and not linea.strip().startswith("--")
        )
        return [pieza for pieza in sin_comentarios.split(";") if pieza.strip()]
