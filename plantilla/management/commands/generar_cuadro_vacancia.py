import datetime
from django.core.management.base import BaseCommand
from django.db import connection
from plantilla.models import CuadroVacancia

class Command(BaseCommand):
    help = 'Genera el cuadro de vacancia diario y lo guarda en el modelo CuadroVacancia'

    def handle(self, *args, **options):
        query = """
        WITH RankedPositions AS (
            SELECT id, `Nº Pos Actual`, `Estado Psn`, `Partida Ptal`
            FROM (
                SELECT id, `Nº Pos Actual`, `Estado Psn`, `Partida Ptal`,
                       ROW_NUMBER() OVER (
                           PARTITION BY `Nº Pos Actual`
                           ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                       ) as rn
                FROM MOV_POS
            ) ranked WHERE rn = 1
        ),
        TargetPositions AS (
            SELECT DISTINCT t.id, t.`Nº Pos Actual`
            FROM RankedPositions t
            INNER JOIN EMPLEADOS_COMPLETOS_SIG e ON e.`Posición` = t.`Nº Pos Actual`
            WHERE t.`Estado Psn` = 'A'
              AND t.`Nº Pos Actual` NOT LIKE '103L%'
              AND t.`Nº Pos Actual` NOT LIKE '1039%'
              AND t.`Partida Ptal` <> '11401'
        ),
        CTE_Vacantes AS (
            SELECT t.`Nº Pos Actual`
            FROM TargetPositions t
            INNER JOIN EMPLEADOS_COMPLETOS_SIG e ON e.`Posición` = t.`Nº Pos Actual`
            WHERE e.`Estado Nómina` = ' '
        )
        SELECT 
            COUNT(t.`Nº Pos Actual`) AS Total,
            SUM(CASE WHEN t.`Nº Pos Actual` LIKE '103%' THEN 1 ELSE 0 END) AS Total_Permanente,
            SUM(CASE WHEN t.`Nº Pos Actual` NOT LIKE '103%' THEN 1 ELSE 0 END) AS Total_Eventual,
            
            SUM(CASE WHEN v.`Nº Pos Actual` IS NULL THEN 1 ELSE 0 END) AS Ocupadas_Total,
            SUM(CASE WHEN v.`Nº Pos Actual` IS NULL AND t.`Nº Pos Actual` LIKE '103%' THEN 1 ELSE 0 END) AS Ocupadas_Permanente,
            SUM(CASE WHEN v.`Nº Pos Actual` IS NULL AND t.`Nº Pos Actual` NOT LIKE '103%' THEN 1 ELSE 0 END) AS Ocupadas_Eventual,
            
            SUM(CASE WHEN v.`Nº Pos Actual` IS NOT NULL THEN 1 ELSE 0 END) AS Vacantes_Total,
            SUM(CASE WHEN v.`Nº Pos Actual` IS NOT NULL AND t.`Nº Pos Actual` LIKE '103%' THEN 1 ELSE 0 END) AS Vacantes_Permanente,
            SUM(CASE WHEN v.`Nº Pos Actual` IS NOT NULL AND t.`Nº Pos Actual` NOT LIKE '103%' THEN 1 ELSE 0 END) AS Vacantes_Eventual
        FROM TargetPositions t
        LEFT JOIN CTE_Vacantes v ON t.`Nº Pos Actual` = v.`Nº Pos Actual`;
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()

        if row:
            total = row[0] or 0
            total_permanente = row[1] or 0
            total_eventual = row[2] or 0
            ocupadas_total = row[3] or 0
            ocupadas_permanente = row[4] or 0
            ocupadas_eventual = row[5] or 0
            vacantes_total = row[6] or 0
            vacantes_permanente = row[7] or 0
            vacantes_eventual = row[8] or 0

            today = datetime.date.today()
            
            obj, created = CuadroVacancia.objects.update_or_create(
                fecha=today,
                defaults={
                    'ocupadas_permanente': ocupadas_permanente,
                    'ocupadas_eventual': ocupadas_eventual,
                    'ocupadas_total': ocupadas_total,
                    'vacantes_permanente': vacantes_permanente,
                    'vacantes_eventual': vacantes_eventual,
                    'vacantes_total': vacantes_total,
                    'total_permanente': total_permanente,
                    'total_eventual': total_eventual,
                    'total': total,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Creado registro CuadroVacancia para {today}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Actualizado registro CuadroVacancia para {today}'))
        else:
            self.stdout.write(self.style.ERROR('No se obtuvieron resultados de la consulta.'))
