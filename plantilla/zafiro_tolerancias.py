"""
Tolerancia de baja de registros por consulta de `importar_zafiro`.

El valor vigente es el de la tabla ZAFIRO_TOLERANCIA_CONSULTA (editable desde
el front, ver ZafiroToleranciasView) y, si la consulta no tiene fila, el valor
por defecto. La tarea corre en la PC Windows (copia_back) y relee esa tabla
justo antes de validar cada consulta; este servidor solo la escribe. Los
valores por defecto deben coincidir con los de settings.py de copia_back
(ZAFIRO_TOLERANCIA_BAJA_PCT / ZAFIRO_TOLERANCIA_COMPLETOS_PCT).
"""

from django.conf import settings

from .models import ZafiroToleranciaConsulta


def tolerancias_por_defecto() -> dict:
    baja = float(getattr(settings, "ZAFIRO_TOLERANCIA_BAJA_PCT", 3))
    completos = float(getattr(settings, "ZAFIRO_TOLERANCIA_COMPLETOS_PCT", 1))
    return {
        "posiciones": baja,
        "completos": completos,
        "bajas": baja,
        "historial": baja,
        "datos_personales": 0.0,
    }


def tolerancias_vigentes() -> dict:
    """Tolerancia (%) por consulta: la configurada en la BD o, si no hay, la por defecto."""
    vigentes = tolerancias_por_defecto()
    for consulta, pct in ZafiroToleranciaConsulta.objects.values_list("consulta", "tolerancia_pct"):
        if consulta in vigentes:
            vigentes[consulta] = float(pct)
    return vigentes
