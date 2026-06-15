import os
import django
import sys

sys.path.append('/home/edgar/ANAM/EjeCentral/eje_central_back')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eje_central_back.settings')
django.setup()

from django.db import connection

def main():
    # Esta query obtiene las posiciones de ambas tablas y busca los que tienen discrepancias en Cd UN o Unidad Adva / Cd UA
    query = """
    WITH MovPosActivos AS (
        SELECT 
            m.`Nº Pos Actual` AS posicion, 
            TRIM(m.`Cd UN`) as cd_un_mov, 
            TRIM(m.`Unidad Adva#`) as cd_ua_mov
        FROM MOV_POS m
        INNER JOIN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY `Nº Pos Actual`
                    ORDER BY `F Efva` DESC, `Fecha Captura` DESC, `F/H Últ Actz` DESC, id DESC
                ) as rn
                FROM MOV_POS
            ) ranked WHERE rn = 1
        ) latest ON m.id = latest.id
        WHERE m.`Estado Psn` = 'A'
    ),
    Empleados AS (
        SELECT 
            TRIM(`Posición`) AS posicion, 
            TRIM(`Cd UN`) AS cd_un_emp, 
            TRIM(`Cd UA`) AS cd_ua_emp
        FROM EMPLEADOS_COMPLETOS_SIG
        WHERE `Posición` IS NOT NULL AND TRIM(`Posición`) != ''
    )
    SELECT 
        m.posicion,
        m.cd_un_mov, e.cd_un_emp,
        m.cd_ua_mov, e.cd_ua_emp
    FROM MovPosActivos m
    INNER JOIN Empleados e ON m.posicion = e.posicion
    WHERE m.cd_un_mov != e.cd_un_emp 
       OR m.cd_ua_mov != e.cd_ua_emp
       OR (m.cd_un_mov IS NULL AND e.cd_un_emp IS NOT NULL)
       OR (m.cd_un_mov IS NOT NULL AND e.cd_un_emp IS NULL)
       OR (m.cd_ua_mov IS NULL AND e.cd_ua_emp IS NOT NULL)
       OR (m.cd_ua_mov IS NOT NULL AND e.cd_ua_emp IS NULL);
    """

    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    diff_un_only = []
    diff_ua_only = []
    diff_both = []

    for row in results:
        pos, un_mov, un_emp, ua_mov, ua_emp = row
        
        # Limpieza por si hay nulos
        un_mov = str(un_mov).strip() if un_mov is not None else ""
        un_emp = str(un_emp).strip() if un_emp is not None else ""
        ua_mov = str(ua_mov).strip() if ua_mov is not None else ""
        ua_emp = str(ua_emp).strip() if ua_emp is not None else ""

        un_diff = (un_mov != un_emp)
        ua_diff = (ua_mov != ua_emp)

        if un_diff and not ua_diff:
            diff_un_only.append((pos, un_mov, un_emp, ua_mov))
        elif ua_diff and not un_diff:
            diff_ua_only.append((pos, un_mov, ua_mov, ua_emp))
        elif un_diff and ua_diff:
            diff_both.append((pos, un_mov, un_emp, ua_mov, ua_emp))

    print(f"Total de posiciones con discrepancias encontradas: {len(results)}\n")

    if diff_ua_only:
        print(f"### Discrepancia en la Unidad Administrativa ({len(diff_ua_only)} posiciones)")
        print("En estos casos, el código maestro Cd UN es el mismo en ambas tablas, pero la Unidad Administrativa específica difiere:\n")
        # Sort by position for predictable output
        for pos, un_mov, ua_mov, ua_emp in sorted(diff_ua_only, key=lambda x: x[0]):
            print(f" • {pos} : En MOV_POS es {ua_mov} | En EMPLEADOS es {ua_emp} (Cd UN: {un_mov})")
        print("\n")

    if diff_un_only:
        print(f"### Discrepancia en el Cd UN ({len(diff_un_only)} posiciones)")
        print("En estos casos, la Unidad Administrativa está correcta en ambas, pero el Código de Unidad no empata:\n")
        for pos, un_mov, un_emp, ua_mov in sorted(diff_un_only, key=lambda x: x[0]):
            print(f" • {pos} : En MOV_POS es {un_mov} | En EMPLEADOS es {un_emp} (Cd UA: {ua_mov})")
        print("\n")

    if diff_both:
        print(f"### Discrepancia en AMBOS campos ({len(diff_both)} posiciones)")
        print("En estos casos, ni el Cd UN ni la Unidad Administrativa coinciden:\n")
        for pos, un_mov, un_emp, ua_mov, ua_emp in sorted(diff_both, key=lambda x: x[0]):
            print(f" • {pos} : MOV_POS(UN: {un_mov}, UA: {ua_mov}) | EMPLEADOS(UN: {un_emp}, UA: {ua_emp})")
        print("\n")

if __name__ == "__main__":
    main()
