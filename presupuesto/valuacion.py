"""
Núcleo de la valuación presupuestaria: cuántos "meses" dura un período y
cuánto cuesta un conjunto de plazas durante ese período.

Vive aparte de `views.py` porque lo consumen dos flujos distintos:
  - El Simulador de Valuación Presupuestaria (``CatalogoPlazasViewSet.calcular``).
  - La generación del Anexo 3 desde el Anexo 2 de Anuencia
    (``AnuenciaAnexo3View`` en ``plantilla/views.py``), que valúa N grupos de
    plazas en una sola petición.

Mantenerlo en un solo lugar evita que las dos rutas se desincronicen: los
importes que el usuario ve en el simulador y los que salen impresos en el
Anexo 3 tienen que ser exactamente los mismos.
"""

from datetime import date, timedelta

from .models import CatalogoPlazas

_UN_DIA = timedelta(days=1)


# --- Duración del período ---------------------------------------------------
# El Anexo 3 oficial NO cuenta días de calendario reales: trabaja en meses
# VIRTUALES de 30 días. Un mes completo siempre vale 1.0 sin importar si el
# mes calendario tiene 28, 30 o 31 días, y el último día real de cualquier mes
# cuenta como el día 30 de ese mes virtual. Por eso arrancar el día 16 de
# cualquier mes vale siempre exactamente 0.5 (la segunda quincena completa).
#
# Verificado contra un Anexo 3 oficial real (UDPCSG): del 16-feb al 31-dic de
# 2026 = 10.5 meses exactos, con lo que las 17 partidas cuadran peso por peso.
#
# Espejo en el front: `calcularMeses` en SimuladorValuacion.jsx — si se toca
# una, hay que tocar la otra.

DIAS_MES_VIRTUAL = 30


def _dia_virtual(f: date) -> int:
    """Día de `f` dentro de un mes virtual de 30 días."""
    if (f + _UN_DIA).month != f.month:  # último día real del mes
        return DIAS_MES_VIRTUAL
    return min(f.day, DIAS_MES_VIRTUAL)


def calcular_meses_periodo(fecha_inicio: date, fecha_fin: date) -> float:
    """Meses de evaluación entre dos fechas, en meses virtuales de 30 días.

    Devuelve 0.0 si el período es inválido (fin anterior al inicio).
    """
    if not fecha_inicio or not fecha_fin or fecha_fin < fecha_inicio:
        return 0.0

    dv_ini = _dia_virtual(fecha_inicio)
    dv_fin = _dia_virtual(fecha_fin)

    if (fecha_inicio.year, fecha_inicio.month) == (fecha_fin.year, fecha_fin.month):
        return max(0, dv_fin - dv_ini + 1) / DIAS_MES_VIRTUAL

    fraccion_inicio = (DIAS_MES_VIRTUAL + 1 - dv_ini) / DIAS_MES_VIRTUAL
    fraccion_fin = dv_fin / DIAS_MES_VIRTUAL
    meses_completos = (
        (fecha_fin.year * 12 + fecha_fin.month) - (fecha_inicio.year * 12 + fecha_inicio.month) - 1
    )
    return fraccion_inicio + max(0, meses_completos) + fraccion_fin


# --- Valuación --------------------------------------------------------------

def calcular_valuacion(meses, plazas_input):
    """Costo de un conjunto de plazas durante `meses`.

    Extraído tal cual de ``CatalogoPlazasViewSet.calcular`` (sin cambios de
    fórmula) para poder reutilizarlo desde la generación del Anexo 3.

    :param meses: duración del período en meses (puede ser fraccionario).
    :param plazas_input: lista de ``{"catalogo_id": int, "plazas": int}``.
    :returns: dict con ``tabla_2022``, ``tabla_q322_t348``, ``subtotal1``,
        ``subtotal2`` y ``total``.
    """
    plazas_map = {item['catalogo_id']: item['plazas'] for item in plazas_input}
    ids = list(plazas_map.keys())

    catalogo = CatalogoPlazas.objects.filter(id__in=ids)

    # Intermediate sums
    u305 = 0  # sueldo
    y305 = 0  # apoyo_capacitacion
    aa305 = 0  # compensacion_garantizada
    w306 = 0  # asignaciones adicionales (despensa + prev_social + ayuda_serv + apoyo_cap + ayuda_trans)
    ab305 = 0  # gastos_medicos (hardcoded to 0 in todo.md example)
    ai305 = 0  # cuota_issste
    aj305 = 0  # cuota_fovissste
    ak305 = 0  # cuota_cesantia
    bh305 = 0  # epr_quincenal (if tiene_epr)

    u_gv1 = 0  # grupo_vacaciones = 1
    u_gv2 = 0  # grupo_vacaciones = 2
    u_gg1 = 0  # grupo_gratificacion = 1
    u_gg2 = 0  # grupo_gratificacion = 2

    total_plazas = 0
    tabla_2022 = []

    # El Anexo 3 oficial NO reporta 15403 como un solo renglón: lo abre en sus
    # 5 componentes, cada uno con su propia clave ("15403 D", "15403 PSM"...).
    # Se acumulan por separado aquí para que el Anexo 3 pueda imprimirlos sin
    # recalcular nada; el simulador simplemente ignora esta llave extra.
    comp_15403 = {"D": 0, "": 0, "PSM": 0, "AS": 0, "T": 0}

    for plaza in catalogo:
        p_qty = plazas_map.get(plaza.id, 0)
        if p_qty <= 0:
            continue

        total_plazas += p_qty

        u305 += float(plaza.sueldo) * p_qty
        y305 += float(plaza.apoyo_capacitacion) * p_qty
        aa305 += float(plaza.compensacion_garantizada) * p_qty

        asignaciones_plaza = (
            float(plaza.despensa)
            + float(plaza.prev_social_multiple)
            + float(plaza.ayuda_servicios)
            + float(plaza.apoyo_capacitacion)
            + float(plaza.ayuda_transporte)
        )
        w306 += asignaciones_plaza * p_qty

        comp_15403["D"] += float(plaza.despensa) * p_qty
        comp_15403["PSM"] += float(plaza.prev_social_multiple) * p_qty
        comp_15403["AS"] += float(plaza.ayuda_servicios) * p_qty
        comp_15403[""] += float(plaza.apoyo_capacitacion) * p_qty
        comp_15403["T"] += float(plaza.ayuda_transporte) * p_qty

        ai305 += float(plaza.cuota_issste) * p_qty
        aj305 += float(plaza.cuota_fovissste) * p_qty
        ak305 += float(plaza.cuota_cesantia) * p_qty

        if plaza.tiene_epr:
            bh305 += float(plaza.epr_quincenal) * p_qty

        if plaza.grupo_vacaciones == 1:
            u_gv1 += float(plaza.sueldo) * p_qty
        else:
            u_gv2 += float(plaza.sueldo) * p_qty

        if plaza.grupo_gratificacion == 1:
            u_gg1 += float(plaza.sueldo) * p_qty
        else:
            u_gg2 += float(plaza.sueldo) * p_qty

        tabla_2022.append({
            "nivel": plaza.nivel,
            "zona": plaza.zona,
            "codigo": plaza.codigo,
            "puesto": plaza.denominacion,
            "plazas": p_qty,
            "sueldo": float(plaza.sueldo),
            "sueldo_colectivo_periodo": float(plaza.sueldo) * p_qty * meses,
            "compensacion": float(plaza.compensacion_garantizada),
            "compensacion_colectiva_periodo": float(plaza.compensacion_garantizada) * p_qty * meses,
        })

    # Calculations for 13201 and 13202
    u322 = u_gv1 + u_gv2 + (u_gv2 * 0.15)
    t_13201 = u322 / 3
    r_13201 = (t_13201 * meses) / 12

    u326 = (u_gg1 / 30) * 40 * 1.35
    u327 = (u_gg2 / 30) * 40 * 1.17
    t_13202 = u326 + u327
    r_13202 = (t_13202 * meses) / 12

    r_12201 = u305 * meses
    t_12201 = u305 * 12
    r_15402 = aa305 * meses
    t_15402 = aa305 * 12

    conceptos_data = [
        ("12201", "Sueldos Base", r_12201, t_12201),
        ("13101", "(Reservado)", 0, 0),
        ("13201", "Primas de vacaciones y dominical", r_13201, t_13201),
        ("13202", "Gratificación de fin de año", r_13202, t_13202),
        ("13409", "(Reservado)", 0, 0),
        ("14101", "Aportaciones ISSSTE", ai305 * meses, ai305 * 12),
        ("14201", "Aportaciones FOVISSSTE", aj305 * meses, aj305 * 12),
        ("14401", "Cuota sindical (1.4%)", (r_12201 + r_15402) * 0.014, (t_12201 + t_15402) * 0.014),
        ("14403", "Cuotas gastos médicos", ab305 * meses, ab305 * 12),
        ("14404", "Seg. separación individualizado", 0, 0),
        ("14405", "Seg. colectivo de retiro", 35.45 * total_plazas * meses, 35.45 * total_plazas * 12),
        ("14301", "Aportación solidaria FOVISSSTE 2%", (u305 + y305) * meses * 0.02, (u305 + y305) * 12 * 0.02),
        ("14105", "Cesantía edad avanzada", ak305 * meses, ak305 * 12),
        ("14302", "Ahorro solidario (res.)", 0, 0),
        ("15402", "Compensación Garantizada", r_15402, t_15402),
        ("15403", "Asignaciones adicionales", w306 * meses, w306 * 12),
    ]

    tabla_q322_t348 = []
    subtotal1 = {"periodo": 0, "anual": 0, "complemento": 0}

    for c, desc, r, t in conceptos_data:
        row = {"concepto": c, "descripcion": desc, "periodo": r, "anual": t, "complemento": t - r}
        tabla_q322_t348.append(row)
        subtotal1["periodo"] += r
        subtotal1["anual"] += t
        subtotal1["complemento"] += (t - r)

    c_15901 = {
        "concepto": "15901",
        "descripcion": "EPR Operativo",
        "periodo": bh305 * meses,
        "anual": bh305 * 12,
        "complemento": (bh305 * 12) - (bh305 * meses),
    }
    tabla_q322_t348.append(c_15901)

    subtotal2 = {
        "periodo": c_15901["periodo"],
        "anual": c_15901["anual"],
        "complemento": c_15901["complemento"],
    }

    total = {
        "periodo": subtotal1["periodo"] + subtotal2["periodo"],
        "anual": subtotal1["anual"] + subtotal2["anual"],
        "complemento": subtotal1["complemento"] + subtotal2["complemento"],
    }

    # Desglose de 15403 en el orden y con las claves del Anexo 3 oficial.
    # (Sólo lo consume el Anexo 3; el simulador ignora esta llave.)
    desglose_15403 = [
        {"concepto": f"15403 {suf}".strip(), "periodo": monto * meses, "anual": monto * 12,
         "complemento": (monto * 12) - (monto * meses)}
        for suf in ("D", "", "PSM", "AS", "T")
        for monto in (comp_15403[suf],)
    ]

    return {
        "tabla_2022": tabla_2022,
        "tabla_q322_t348": tabla_q322_t348,
        "subtotal1": subtotal1,
        "subtotal2": subtotal2,
        "total": total,
        "desglose_15403": desglose_15403,
    }
