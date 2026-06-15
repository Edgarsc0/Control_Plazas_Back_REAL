import os
import sys
import time
import django

# Setup django environment
sys.path.append("/home/edgar/ANAM/EjeCentral/eje_central_back")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eje_central_back.settings")
django.setup()

from django.conf import settings
from plantilla.tasks import (
    _importar_csv_posiciones,
    _importar_csv_empleados_completos,
    _importar_csv_bajas,
    _swap_blue_green_tables,
    _corregir_csv
)
from plantilla.models import ZafiroBitacora

def main():
    print("==================================================================")
    print("INICIANDO SIMULACIÓN DE ACTUALIZACIÓN BLUE-GREEN CON CERO DOWNTIME")
    print("==================================================================")
    print("Durante esta simulación (que durará aprox. 40-50 segundos), navega")
    print("por la aplicación frontend. Deberías seguir viendo todos los datos")
    print("en tiempo real sin pantallas vacías ni interrupciones.")
    print("==================================================================")
    
    start_time = time.time()
    download_dir = settings.ZAFIRO_DOWNLOAD_DIR
    script_path = settings.ZAFIRO_SCRIPT_PATH
    
    # Simular la creación de la bitácora
    bitacora = ZafiroBitacora.objects.create(
        status="RUNNING_SIMULATION",
        es_historico=False,
        logs_en_vivo="[SIMULACION] Iniciada"
    )
    
    # 1. Corrección heurística
    print("\n[Paso 1/4] Aplicando corrector heurístico a los CSVs locales...")
    csv_pos = os.path.join(download_dir, "zafiro_info_Posiciones.csv")
    csv_emp = os.path.join(download_dir, "zafiro_info_Empleados_Completo.csv")
    csv_baj = os.path.join(download_dir, "zafiro_info_Empleados_Bajas.csv")
    
    csv_pos_corregido = _corregir_csv(csv_pos, script_path, bitacora)
    csv_emp_corregido = _corregir_csv(csv_emp, script_path, bitacora)
    csv_baj_corregido = _corregir_csv(csv_baj, script_path, bitacora)
    print("Corrección finalizada.")
    
    # 2. Carga en tablas Staging
    print("\n[Paso 2/4] Cargando ~70,000 registros en tablas de STAGING (sombra)...")
    print("  -> Este paso es el más tardado. La base de datos de producción sigue intacta.")
    
    t_load_start = time.time()
    
    print("  -> Cargando posiciones en MOV_POS_STAGING...")
    total_pos = _importar_csv_posiciones(csv_pos_corregido, False, bitacora)
    print(f"     Listo. {total_pos} posiciones cargadas.")
    
    print("  -> Cargando empleados en EMPLEADOS_COMPLETOS_SIG_STAGING...")
    total_emp = _importar_csv_empleados_completos(csv_emp_corregido, False, bitacora)
    print(f"     Listo. {total_emp} empleados cargados.")
    
    print("  -> Cargando bajas en BAJAS_SIG_STAGING...")
    total_baj = _importar_csv_bajas(csv_baj_corregido, False, bitacora)
    print(f"     Listo. {total_baj} bajas cargadas.")
    
    load_duration = round(time.time() - t_load_start, 2)
    print(f"Carga en staging completada en {load_duration}s.")
    
    # 3. Intercambio atómico
    print("\n[Paso 3/4] Ejecutando RENAME TABLE atómico en la base de datos (Swap)...")
    t_swap_start = time.time()
    _swap_blue_green_tables(bitacora)
    swap_duration = round((time.time() - t_swap_start) * 1000, 2)
    print(f"Swap completado en {swap_duration} milisegundos!")
    
    # 4. Invalida caché
    print("\n[Paso 4/4] Invalidando caché del frontend...")
    try:
        from django.core.cache import cache
        cache_keys = [
            "active_position_codes",
            "plantilla_vacantes_por_nivel",
            "plantilla_vacantes_por_nivel_resumen",
            "empleados_completos_estatus_resumen",
            "empleados_completos_activos_detalle",
            "empleados_estatus_por_nivel_ua",
            "empleados_distribucion_geografica",
            "mov_pos_detalle",
            "bajas_sig_list",
            "bajas_motivos_pie",
            "bajas_historico",
            "movimientos_personal_stats"
        ]
        cache.delete_many(cache_keys)
        print("Caché invalidada con éxito.")
    except Exception as e:
        print(f"Advertencia al borrar caché: {e}")
        
    bitacora.status = "EXITO"
    bitacora.save()
    
    total_duration = round(time.time() - start_time, 2)
    print("\n==================================================================")
    print(f"SIMULACIÓN COMPLETADA EXITOSAMENTE en {total_duration}s.")
    print("El frontend ha cambiado instantáneamente a los nuevos datos.")
    print("==================================================================")

if __name__ == "__main__":
    main()
