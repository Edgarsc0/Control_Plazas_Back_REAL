"""
rotacion_direccion_general.py
==============================
Reconstruye la línea de tiempo de ocupación de UNA dirección general
(`cd_puesto` recibido como parámetro) a partir de cp_tbl_mov_completo_29_05_26.

Mismo espíritu que plantilla/rotacion_aduanas.py (lógica pura en Python, sin
stored procedure, cacheada en la vista) pero con una diferencia estructural:
en aduanas, tener `cd_puesto IN PUESTOS_TITULARIDAD` basta para ser titular
(dos códigos fijos, sin ambigüedad). Aquí NO — el mismo `cd_puesto` de
dirección general puede tener filas de personal que no son realmente el
director (subordinados capturados bajo el mismo código de puesto funcional,
o el propio titular en un nivel jerárquico previo a su nombramiento como
titular). Se determinó de forma empírica (ver "Rotación de directores
generales.md" en la raíz del repo, sesión 2026-09-09) que el nivel jerárquico
real del titular es el `nv_jerarquico` MÁS BAJO observado para ese cd_puesto
— cualquier fila con un nivel distinto no cuenta como gestión de titularidad.


Las cuatro decisiones que sostienen el resultado
-------------------------------------------------

1. "¿Quién es realmente el director?" se resuelve con `nv_jerarquico`, no con
   el `cd_puesto` a secas — Y, para las 12 direcciones generales que el
   usuario ya identificó a mano, ADEMÁS con `id_depto`.

   `nivel_dg(cd_puesto)` = MIN(nv_jerarquico) entre TODAS las filas de ese
   cd_puesto en cp_tbl_mov_completo_29_05_26. Una fila solo cuenta como
   gestión de titularidad si `cd_puesto` coincide Y `nv_jerarquico` coincide
   con ese mínimo. Esto excluye, por ejemplo, la fila de contratación de un
   empleado que entra a un nivel subordinado y es promovido a director el
   mismo cd_puesto días después (nv_jerarquico baja de 3 a 2 en el mismo
   puesto) — esa fila de nv=3 no es una gestión de titularidad.

   Con nv_jerarquico SOLO, algunos cd_puesto siguen trayendo de más (p. ej.
   AD2054 da 11 "candidatos" con el nv mínimo, cuando el usuario ya había
   verificado a mano que solo 3 son realmente el director — ver "Rotación de
   directores generales.md"). El filtro final, acordado explícitamente con
   el usuario el 2026-09-09, es: de los candidatos con nv mínimo, quedarse
   solo con los que en su ÚLTIMO movimiento DENTRO de ese subconjunto (nv
   mínimo, no su último movimiento absoluto) tienen el `id_depto` objetivo de
   esa dirección general — ver `ID_DEPTO_OBJETIVO_POR_CD_PUESTO`. Es una
   corrección de roster (a nivel EMPLEADO), no de fila: una vez que alguien
   califica, TODAS sus filas de nv mínimo en ese cd_puesto cuentan para su
   gestión, el filtro de id_depto solo decide si entra o no a la línea de
   tiempo.

   Excepción explícita del usuario: **AD2353** no lleva filtro de id_depto
   (el filtro de id_depto ahí daba solo 1 candidato de 3 reales; se usa nv
   mínimo a secas). Por eso `ID_DEPTO_OBJETIVO_POR_CD_PUESTO` no tiene
   entrada para AD2353.

   Este mapeo de id_depto es conocimiento externo que el usuario dio
   directamente (código de 3 dígitos + 8 ceros a la derecha) para estas 12
   direcciones generales específicas — NO es derivable de los datos, y NO
   generaliza a un cd_puesto arbitrario fuera de esta lista: para cualquier
   otro cd_puesto, el filtro de id_depto simplemente no se aplica (se queda
   en nv_jerarquico mínimo a secas).

2. Se ordena por (fecha_efectiva, sec, id) — NUNCA por (fecha_efectiva, id).

   Encontrado en la misma sesión: dos movimientos del mismo día se desempatan
   por `sec`, no por `id` (el `id` es un autoincremental de carga, no refleja
   el orden cronológico intradía). Ignorar esto hizo que dos bajas reales
   (mismo día que un ajuste salarial, con `sec` mayor) se leyeran como "sigue
   activo" — ver Daniel Ortiz Fernández y Citlalli Navarro Del Rosario en el
   documento de la sesión. `rotacion_aduanas.py` ya ordena así; aquí se
   replica el mismo criterio.

3. La fecha de salida sale de la trayectoria COMPLETA del empleado, no solo
   de sus filas en ese cd_puesto — igual que aduanas (nota 3 de ese módulo).
   Si el tramo cierra en TER/TE1 esa es la salida. Si no, la salida real es
   el siguiente movimiento del empleado (que ya está en otro puesto, o en el
   mismo puesto pero fuera del nivel de titularidad) — en el 100% de los
   casos observados para las 12 direcciones generales analizadas fue un
   traslado, nunca una baja no capturada.


Insubsistencias
----------------
Una insubsistencia (nombramiento declarado insubsistente, el titular nunca
llegó a ejercer realmente) es, con este modelo, una BAJA (accion TER/TE1)
cuyo `motivo_nombre` contiene el texto "insubsistencia" — exactamente el
mismo criterio que usa el frontend de rotación de aduanas
(`esInsubsistencia` en RotacionAduanasSubTab.jsx). Se expone aquí como
`es_insubsistencia` en cada gestión para no duplicar ese criterio en el
frontend.
"""

from collections import defaultdict

# Acciones que cierran una gestión por baja del sistema.
ACCIONES_BAJA = frozenset({"TER", "TE1"})

# Clasificación de la salida de una gestión.
SALIDA_BAJA = "BAJA"
SALIDA_ACTIVO = "ACTIVO"
SALIDA_PUESTO = "SALIDA_PUESTO"
# Caso borde: el empleado sigue en el MISMO cd_puesto pero su siguiente fila
# ya no tiene el nv_jerarquico de titularidad (p. ej. una degradación sin
# cambio de puesto funcional). No se observó en los 12 cd_puesto analizados
# el 2026-09-09, pero el algoritmo lo distingue en vez de mezclarlo con
# SALIDA_PUESTO para no ocultar un caso real si aparece en otro cd_puesto.
SALIDA_CAMBIO_NIVEL = "CAMBIO_NIVEL"

# id_depto OBJETIVO por cd_puesto — dato externo que dio el usuario
# directamente (código de 3 dígitos + 8 ceros a la derecha), ver nota 1 del
# encabezado. Sin entrada para AD2353: excepción explícita, ese cd_puesto
# usa solo nv_jerarquico mínimo. Para cualquier cd_puesto fuera de esta
# lista (no es una de las 12 direcciones generales ya identificadas) el
# filtro de id_depto tampoco se aplica — se cae a nv_jerarquico mínimo a
# secas, ver roster_valido().
ID_DEPTO_OBJETIVO_POR_CD_PUESTO = {
    "OI1001": 200000000,
    "EV1001": 300000000,
    "AD2054": 10000000000,
    "AD2052": 20000000000,
    "AD2049": 30000000000,
    "AD2056": 40000000000,
    "AD2055": 50000000000,
    "RE1001": 60000000000,
    "CT1001": 70000000000,
    "AD2354": 80000000000,
    "RS1001": 90000000000,
}


def _nombre_completo(mov):
    partes = [mov.get("nombre"), mov.get("ap_pat"), mov.get("ap_mat")]
    return " ".join(p for p in partes if p).strip()


def _clave_orden(mov):
    """Orden cronológico dentro de la trayectoria de UN empleado.

    `id` es desempate de último recurso; el desempate real de movimientos
    del mismo día es `sec` — ver nota 2 del encabezado del módulo.
    """
    return (mov["fecha_efectiva"], mov.get("sec") or 0, mov.get("id") or 0)


def _nivel_numerico(mov):
    """`nv_jerarquico` a entero, o None si viene vacío/no numérico."""
    valor = (
        (mov.get("nv_jerarquico") or "").strip()
        if isinstance(mov.get("nv_jerarquico"), str)
        else mov.get("nv_jerarquico")
    )
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def nivel_direccion_general(movimientos, cd_puesto):
    """MIN(nv_jerarquico) entre las filas de `cd_puesto` — ver nota 1 del
    encabezado. `movimientos` puede traer trayectorias completas de varios
    empleados; se filtra aquí por `cd_puesto` antes de tomar el mínimo."""
    niveles = [
        _nivel_numerico(m)
        for m in movimientos
        if m.get("cd_puesto") == cd_puesto and _nivel_numerico(m) is not None
    ]
    return min(niveles) if niveles else None


def _es_titular(mov, cd_puesto, nivel_dg):
    return mov.get("cd_puesto") == cd_puesto and _nivel_numerico(mov) == nivel_dg


def _id_depto_numerico(mov):
    """`id_depto` a entero, ignorando el padding inconsistente de la tabla
    (a veces 9 dígitos, a veces 11 para el mismo departamento) — comparar
    siempre numérico, nunca por igualdad de string. Ver "Rotación de
    directores generales.md", bug de datos #1."""
    valor = (
        (mov.get("id_depto") or "").strip()
        if isinstance(mov.get("id_depto"), str)
        else mov.get("id_depto")
    )
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def roster_valido(movimientos, cd_puesto, nivel_dg):
    """Empleados que cuentan como titulares reales de `cd_puesto` — ver nota 1
    del encabezado del módulo.

    Candidatos: quienes tienen AL MENOS una fila cd_puesto+nv_jerarquico ==
    nivel_dg. Si `cd_puesto` tiene un id_depto objetivo (no es AD2353, y sí
    es una de las 12 direcciones generales ya identificadas), se filtra
    además: el candidato entra al roster solo si su fila MÁS RECIENTE dentro
    de ese subconjunto (nv_jerarquico == nivel_dg, no su último movimiento
    absoluto) tiene ese id_depto. Sin id_depto objetivo para `cd_puesto`
    (incluye AD2353 y cualquier cd_puesto fuera de las 12), el roster es
    simplemente todos los candidatos.
    """
    por_empleado = defaultdict(list)
    for mov in movimientos:
        if mov.get("cd_puesto") == cd_puesto and _nivel_numerico(mov) == nivel_dg:
            por_empleado[mov.get("num_empleado")].append(mov)

    id_depto_objetivo = ID_DEPTO_OBJETIVO_POR_CD_PUESTO.get(cd_puesto)
    if id_depto_objetivo is None:
        return set(por_empleado.keys())

    validos = set()
    for num_empleado, filas in por_empleado.items():
        filas.sort(key=_clave_orden)
        if _id_depto_numerico(filas[-1]) == id_depto_objetivo:
            validos.add(num_empleado)
    return validos


def _fila_completa(mov, catalogo_puestos=None):
    """Copia una fila de movimiento tal cual la trajo el SQL, con `sal_base`
    ya convertido a float (Decimal de MySQL) — mismo criterio que
    rotacion_aduanas._fila_completa, para que el consumidor pueda diffear
    campo por campo contra el registro cronológico inmediato anterior.

    `catalogo_puestos` ({cd_pto_funcional: nombre_puesto_funcional}, desde
    CAT_PTO_FUNC) agrega el nombre del puesto funcional de ESTA fila — mismo
    criterio que rotacion_aduanas._fila_completa: es lo que permite que
    Procedencia/Destino muestren el nombre del puesto de origen/destino, no
    solo el código crudo.
    """
    if mov is None:
        return None
    fila = dict(mov)
    if fila.get("sal_base") is not None:
        fila["sal_base"] = float(fila["sal_base"])
    if catalogo_puestos is not None:
        fila["nombre_puesto_funcional"] = catalogo_puestos.get(
            (fila.get("cd_puesto") or "").strip()
        )
    return fila


def _es_insubsistencia(motivo_nombre):
    return "insubsistencia" in (motivo_nombre or "").lower()


def segmentar_trayectoria(trayectoria, cd_puesto, nivel_dg, catalogo_puestos=None):
    """Parte la trayectoria de un empleado en gestiones de titularidad de
    `cd_puesto` al nivel jerárquico `nivel_dg`.

    Un tramo es una racha contigua de filas que cumplen `_es_titular`. El par
    TE1 + RE1 el mismo día (fin y reingreso de nombramiento, distinguidos por
    `sec`) cae en el mismo tramo si ambas filas siguen siendo del nivel DG —
    mismo criterio que rotacion_aduanas.segmentar_trayectoria.
    """
    gestiones = []
    i = 0
    total = len(trayectoria)

    while i < total:
        if not _es_titular(trayectoria[i], cd_puesto, nivel_dg):
            i += 1
            continue

        j = i
        while j + 1 < total and _es_titular(trayectoria[j + 1], cd_puesto, nivel_dg):
            j += 1

        tramo = trayectoria[i : j + 1]
        siguiente = trayectoria[j + 1] if j + 1 < total else None
        gestiones.append(
            _armar_gestion(
                tramo,
                siguiente,
                trayectoria[i - 1] if i > 0 else None,
                catalogo_puestos,
            )
        )
        i = j + 1

    return gestiones


def _armar_gestion(tramo, siguiente, previo, catalogo_puestos=None):
    entrada = tramo[0]
    ultimo = tramo[-1]

    if ultimo.get("accion") in ACCIONES_BAJA:
        salida, tipo = ultimo, SALIDA_BAJA
    elif siguiente is None:
        salida, tipo = None, SALIDA_ACTIVO
    else:
        salida = siguiente
        if siguiente.get("accion") in ACCIONES_BAJA:
            tipo = SALIDA_BAJA
        elif siguiente.get("cd_puesto") == entrada.get("cd_puesto"):
            # Mismo cd_puesto, pero ya no calificó como titular (nivel
            # jerárquico distinto) — ver SALIDA_CAMBIO_NIVEL.
            tipo = SALIDA_CAMBIO_NIVEL
        else:
            tipo = SALIDA_PUESTO

    salida_motivo_nombre = salida.get("motivo_nombre") if salida else None

    return {
        "num_empleado": entrada.get("num_empleado"),
        "nombre": _nombre_completo(entrada),
        "sexo": entrada.get("sexo"),
        "cd_puesto": entrada.get("cd_puesto"),
        "nombre_puesto_funcional": (
            catalogo_puestos.get((entrada.get("cd_puesto") or "").strip())
            if catalogo_puestos is not None
            else None
        ),
        "posicion_entrada": entrada.get("posicion"),
        "posiciones": sorted({m.get("posicion") for m in tramo if m.get("posicion")}),
        "nivel_tabular": entrada.get("nivel_tabular"),
        "id_depto": entrada.get("id_depto"),
        "fecha_entrada": entrada.get("fecha_efectiva"),
        "entrada_accion": entrada.get("accion"),
        "entrada_accion_nombre": entrada.get("accion_nombre"),
        "entrada_motivo": entrada.get("motivo"),
        "entrada_motivo_nombre": entrada.get("motivo_nombre"),
        "entrada_fecha_captura": entrada.get("fecha_captura"),
        "entrada_completo": _fila_completa(entrada, catalogo_puestos),
        "fecha_salida": salida.get("fecha_efectiva") if salida else None,
        "salida_accion": salida.get("accion") if salida else None,
        "salida_accion_nombre": salida.get("accion_nombre") if salida else None,
        "salida_motivo": salida.get("motivo") if salida else None,
        "salida_motivo_nombre": salida_motivo_nombre,
        "salida_fecha_captura": salida.get("fecha_captura") if salida else None,
        "salida_destino_puesto": (
            salida.get("cd_puesto")
            if salida and tipo in (SALIDA_PUESTO, SALIDA_CAMBIO_NIVEL)
            else None
        ),
        "salida_destino_posicion": (
            salida.get("posicion") if salida and tipo != SALIDA_BAJA else None
        ),
        "salida_completo": _fila_completa(salida, catalogo_puestos) if salida else None,
        "tipo_salida": tipo,
        # Ver nota "Insubsistencias" del encabezado — mismo criterio que
        # esInsubsistencia en RotacionAduanasSubTab.jsx, calculado aquí para
        # no duplicarlo en el frontend.
        "es_insubsistencia": tipo == SALIDA_BAJA
        and _es_insubsistencia(salida_motivo_nombre),
        # Procedencia: el registro INMEDIATO ANTERIOR al primer registro de
        # esta gestión, en la historia COMPLETA del empleado (no solo dentro
        # de este cd_puesto) — de dónde venía antes de convertirse en
        # director. None si esta es la primerísima fila de su historia.
        "origen_completo": _fila_completa(previo, catalogo_puestos)
        if previo is not None
        else None,
        "total_movimientos": len(tramo),
        "movimientos": [_fila_completa(m, catalogo_puestos) for m in tramo[1:]],
    }


def calcular_vacancias(gestiones, hoy):
    """Huecos entre la salida de una gestión y la entrada de la siguiente —
    idéntico a rotacion_aduanas.calcular_vacancias. La última queda abierta
    si la gestión más reciente ya cerró (baja, cambio de nivel o traslado) y
    nadie ha vuelto a ocupar el puesto al nivel de titularidad."""
    vacancias = []

    for actual, siguiente in zip(gestiones, gestiones[1:]):
        fin = actual["fecha_salida"]
        inicio = siguiente["fecha_entrada"]
        if fin and inicio > fin:
            vacancias.append(
                {
                    "desde": fin,
                    "hasta": inicio,
                    "dias": (inicio - fin).days,
                    "sale": actual["nombre"],
                    "motivo_salida": actual["salida_motivo_nombre"],
                    "tipo_salida": actual["tipo_salida"],
                    "entra": siguiente["nombre"],
                    "motivo_entrada": siguiente["entrada_motivo_nombre"],
                    "abierta": False,
                }
            )

    if gestiones:
        ultima = gestiones[-1]
        if ultima["tipo_salida"] != SALIDA_ACTIVO and ultima["fecha_salida"]:
            vacancias.append(
                {
                    "desde": ultima["fecha_salida"],
                    "hasta": None,
                    "dias": (hoy - ultima["fecha_salida"]).days,
                    "sale": ultima["nombre"],
                    "motivo_salida": ultima["salida_motivo_nombre"],
                    "tipo_salida": ultima["tipo_salida"],
                    "entra": None,
                    "motivo_entrada": None,
                    "abierta": True,
                }
            )

    return vacancias


def anotar_consecutivos(gestiones):
    """Numera cada gestión en orden cronológico — mismo criterio que
    `anotarConsecutivos` en RotacionAduanasSubTab.jsx: cuenta titulares
    REALES, así que una gestión declarada insubsistente (nunca llegó a
    ejercer) NO avanza el contador y se queda con `consecutivo = None`.
    Muta `gestiones` in place (agrega la llave `consecutivo`) y devuelve el
    último consecutivo asignado (= número de titulares reales).
    """
    consecutivo = 0
    for gestion in gestiones:
        if gestion["es_insubsistencia"]:
            gestion["consecutivo"] = None
            continue
        consecutivo += 1
        gestion["consecutivo"] = consecutivo
    return consecutivo


def construir_historia_direccion_general(
    movimientos, cd_puesto, hoy, catalogo_puestos=None
):
    """Punto de entrada. `movimientos` son TODAS las filas de la trayectoria
    de cada empleado que alguna vez tuvo `cd_puesto`, no solo sus filas en ese
    puesto (ver nota 3 del encabezado). Lógica pura: no toca la base ni
    Django, la vista (HistoriaDireccionGeneralView) hace el SQL.

    `catalogo_puestos` ({cd_pto_funcional: nombre_puesto_funcional}, desde
    CAT_PTO_FUNC) es opcional; sin él se omite el nombre de puesto funcional
    en procedencia/destino (queda solo el código crudo).

    Devuelve None si `cd_puesto` no tiene ninguna fila con `nv_jerarquico`
    válido (no se puede determinar el nivel de titularidad).
    """
    nivel_dg = nivel_direccion_general(movimientos, cd_puesto)
    if nivel_dg is None:
        return None

    # Roster de empleados que SÍ cuentan como titulares reales — ver nota 1
    # del encabezado. nv_jerarquico mínimo solo no basta para varios de los
    # 12 cd_puesto ya identificados (p. ej. AD2054 da 11 candidatos con nv
    # mínimo, de los cuales solo 3 son el director real); el filtro de
    # id_depto (cuando aplica) reduce el roster a los empleados correctos.
    roster = roster_valido(movimientos, cd_puesto, nivel_dg)

    por_empleado = defaultdict(list)
    for mov in movimientos:
        if mov.get("num_empleado") in roster:
            por_empleado[mov.get("num_empleado")].append(mov)

    gestiones = []
    filas_excluidas_por_nivel = 0
    filas_excluidas_por_roster = 0
    for trayectoria in por_empleado.values():
        trayectoria.sort(key=_clave_orden)
        gestiones.extend(
            segmentar_trayectoria(trayectoria, cd_puesto, nivel_dg, catalogo_puestos)
        )
        filas_excluidas_por_nivel += sum(
            1
            for m in trayectoria
            if m.get("cd_puesto") == cd_puesto and _nivel_numerico(m) != nivel_dg
        )
    for mov in movimientos:
        if (
            mov.get("cd_puesto") == cd_puesto
            and _nivel_numerico(mov) == nivel_dg
            and mov.get("num_empleado") not in roster
        ):
            filas_excluidas_por_roster += 1

    gestiones.sort(key=lambda g: g["fecha_entrada"])
    for gestion in gestiones:
        gestion["dias_gestion"] = (
            (gestion["fecha_salida"] or hoy) - gestion["fecha_entrada"]
        ).days

    # Consecutivo ANTES de calcular vacancias — igual que aduanas, es un
    # atributo de la gestión, no de la línea de tiempo completa.
    total_titulares_reales = anotar_consecutivos(gestiones)

    vacancias = calcular_vacancias(gestiones, hoy) if gestiones else []
    titular = next((g for g in gestiones if g["tipo_salida"] == SALIDA_ACTIVO), None)
    insubsistencias = [g for g in gestiones if g["es_insubsistencia"]]

    return {
        "cd_puesto": cd_puesto,
        "nombre_puesto_funcional": (
            catalogo_puestos.get(cd_puesto) if catalogo_puestos is not None else None
        ),
        "nivel_jerarquico_titularidad": nivel_dg,
        "corte": hoy,
        "titular_actual": titular["nombre"] if titular else None,
        "titular_actual_num_empleado": titular["num_empleado"] if titular else None,
        "titular_actual_consecutivo": titular["consecutivo"] if titular else None,
        "titular_desde": titular["fecha_entrada"] if titular else None,
        "puesto_vacante": titular is None,
        "total_gestiones": len(gestiones),
        "total_titulares": len({g["num_empleado"] for g in gestiones}),
        # Número de titulares REALES (excluye insubsistencias) — el último
        # consecutivo asignado. Mismo criterio que "Titulares" en el resumen
        # de rotación de aduanas.
        "total_titulares_reales": total_titulares_reales,
        "total_vacancias": len(vacancias),
        "dias_acefalia": sum(v["dias"] for v in vacancias),
        "total_insubsistencias": len(insubsistencias),
        # Cuántas filas de este cd_puesto NO se contaron como titularidad por
        # no tener el nv_jerarquico mínimo — la transparencia que pide la
        # nota 1 del encabezado: "no todos los que tienen el código de
        # puesto son realmente directores generales".
        "filas_excluidas_por_nivel_jerarquico": filas_excluidas_por_nivel,
        # Candidatos con nv_jerarquico mínimo pero excluidos del roster por
        # no tener el id_depto objetivo en su último movimiento del
        # subconjunto — 0 si `cd_puesto` no tiene id_depto objetivo definido
        # (AD2353, o cualquier cd_puesto fuera de las 12).
        "filas_excluidas_por_id_depto": filas_excluidas_por_roster,
        "gestiones": gestiones,
        "vacancias": vacancias,
    }
