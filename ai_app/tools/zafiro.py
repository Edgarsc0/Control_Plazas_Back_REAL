from plantilla.models import ZafiroBitacora
from ._base import tool_handler

@tool_handler(max_output_chars=6000)
def estado_sincronizacion_zafiro() -> str:
    """
    Consulta la bitácora de sincronización del sistema ZAFIRO (SAP) con la base de datos de la ANAM.

    Retorna la fecha y hora de la última ejecución, duración, cantidad de registros actualizados
    (plazas, nómina y bajas), estatus de éxito/falla y errores recientes si ocurrieron.
    """
    bitacora = list(ZafiroBitacora.objects.all().order_by("-fecha_ejecucion")[:5])

    if not bitacora:
        return "⚠️ No hay registros de sincronización de ZAFIRO en la bitácora."

    ultimo = bitacora[0]
    
    res = "🔄 ESTADO DE SINCRONIZACIÓN ZAFIRO (SAP)\n"
    res += "════════════════════════════════════════════════════════\n"
    
    emoji_status = "✅ EXITOSO" if ultimo.status == "OK" else "❌ FALLIDO"
    res += f"Última Ejecución: {ultimo.fecha_ejecucion.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
    res += f"Estatus: {emoji_status} (Código: {ultimo.status})\n"
    res += f"Duración: {ultimo.duracion_segundos or 0:.1f} segundos\n\n"
    
    res += "📊 Registros Importados en Última Carga:\n"
    res += f"  - Plazas (MOV_POS): {ultimo.registros_posiciones:,} registros\n"
    res += f"  - Empleados en Nómina (SIG): {ultimo.registros_completos:,} registros\n"
    res += f"  - Bajas/Desincorporaciones: {ultimo.registros_bajas:,} registros\n"
    res += f"  - Historial Posición: {getattr(ultimo, 'registros_historial', 0):,} registros\n"
    
    if ultimo.error_message:
        res += f"\n❌ Mensaje de Error en Última Sincronización:\n  {ultimo.error_message}\n"

    res += "\n📜 Historial de Últimas 5 Sincronizaciones:\n"
    for item in bitacora:
        item_status = "✅ OK" if item.status == "OK" else f"❌ {item.status}"
        res += f"  - {item.fecha_ejecucion.strftime('%Y-%m-%d %H:%M:%S')} | Estatus: {item_status} | Duración: {item.duracion_segundos or 0:.1f}s | Plazas: {item.registros_posiciones} | SIG: {item.registros_completos} | Bajas: {item.registros_bajas} | Historial: {getattr(item, 'registros_historial', 0)}\n"

    return res.strip()
