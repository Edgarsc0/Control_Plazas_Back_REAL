"""
rotacion_aduanas.py
===================
Reconstruye la línea de tiempo de titularidad de las 50 aduanas del país a
partir de cp_tbl_mov_completo_29_05_26, para los puestos AD2347
("Administrador de Aduana Tipo 1") y AD3004 ("Administrador de Aduana Tipo 2").

La tabla de movimientos NO registra vacancias: toda fila trae un empleado. La
titularidad, su fecha de salida y los periodos en que una aduana quedó acéfala
son derivados aquí.

Este módulo es lógica pura: recibe filas como dicts y no toca la base ni Django.
La vista (RotacionTitularesAduanasView en views.py) hace el SQL y llama a
`construir_rotacion`. Así el algoritmo se puede probar sin base de datos —
ver plantilla/tests.py.


Las cuatro decisiones que sostienen el resultado
------------------------------------------------

1. La aduana se identifica por `un_admin` leído contra el catálogo de su época,
   no por `desc_larga_un` ni por `id_depto`.

   El catálogo autoritativo es `SELECT DISTINCT \\`Cd UA\\`, \\`Unidad Administrativa\\`
   FROM EMPLEADOS_COMPLETOS_SIG`: 65 códigos, de los cuales 101-150 son
   exactamente las 50 aduanas.

   CUIDADO — la alineación organizacional del 2022-07-01 RENUMERÓ las unidades:
   30 de los 50 códigos cambiaron de aduana ese día (el 101 era Aguascalientes y
   pasó a ser Agua Prieta; el 123 era Cancún y pasó a ser Altamira; el 150 era
   Ciudad Juárez y pasó a ser México). Solo 11 conservaron su significado.
   Por eso el catálogo se aplica por época — ver FECHA_RENUMERACION.

   Agrupar por el código crudo produce 69 columnas en vez de 50 y 121 traslados
   en vez de 73, casi la mitad falsos. Aplicar el catálogo nuevo a todo es peor
   porque no se nota: da las 50 columnas correctas pero mete 29 traslados falsos
   en el primer semestre de 2022.

   `id_depto` se descartó: va desfasado respecto de `un_admin` en ~10 000 filas.

2. Se ordena por empleado, no por aduana.

   Ordenando la trayectoria de cada titular por (fecha_efectiva, sec) no hay
   NI UN empate en las 922 filas del universo: el orden es determinista y no
   hace falta ningún criterio de desempate inventado. Ordenar a nivel aduana sí
   produce empates entre la baja de un titular y el alta de su sucesor el mismo
   día, y ahí `id` no ayuda porque no es cronológico (dentro de una plaza los
   ids decrecen).

3. La fecha de salida sale de la trayectoria, no de la aduana.

   Si el tramo cierra en TER/TE1 esa es la salida. Si no, la salida es el
   siguiente movimiento del empleado, que por construcción ya está en otra
   aduana o en otro puesto. Con esto las 213 gestiones cierran con un
   movimiento real: ninguna requiere inferencia.

4. Cuando MOV_POS contradice a la fila de personal por una alineación
   organizacional, manda MOV_POS.

   Cruzados los 728 movimientos de titularidad contra la adscripción que
   MOV_POS le da a cada plaza, coinciden 725. De las 3 discrepancias, dos son
   de la plaza 10334530 el 2022-07-01: personal se quedó con el código viejo
   (123 → Altamira) cuando la plaza ya estaba renumerada (124 → Cancún). La
   tercera es simultaneidad real (la baja de un titular el mismo día que su
   plaza cambió de adscripción) y NO debe corregirse; por eso el override solo
   se aplica cuando el motivo en MOV_POS es una alineación organizacional.


Cifras de referencia al corte 2026-08-29
----------------------------------------
50 aduanas · 57 plazas · 138 titulares · 213 gestiones · 44 vacancias
Salidas: 84 bajas, 73 traslados entre aduanas, 48 titulares activos,
8 salidas hacia otro puesto.
"""

import datetime
import re
from collections import defaultdict

# Los dos puestos que representan la titularidad de una aduana.
PUESTOS_TITULARIDAD = ("AD2347", "AD3004")

# Día de la alineación organizacional que renumeró las unidades administrativas.
# Las filas con fecha_efectiva >= a esta fecha usan el catálogo vigente; las
# anteriores usan la numeración previa. Ver nota 1 del encabezado.
FECHA_RENUMERACION = datetime.date(2022, 7, 1)

# Rango de `Cd UA` que corresponde a las aduanas dentro del catálogo.
CD_UA_ADUANA_MIN = 101
CD_UA_ADUANA_MAX = 150

# Acciones que cierran una gestión por baja del sistema.
ACCIONES_BAJA = frozenset({"TER", "TE1"})

# Clasificación de la salida de una gestión.
SALIDA_BAJA = "BAJA"
SALIDA_TRASLADO = "TRASLADO_ADUANA"
SALIDA_OTRO_PUESTO = "SALIDA_PUESTO"
SALIDA_ACTIVO = "ACTIVO"


def normalizar_unidad(texto):
    """Colapsa espacios repetidos. `desc_larga_un` trae doble espacio antes de
    "con sede" y el catálogo no, así que sin esto las dos fuentes nunca empatan."""
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def es_aduana(cd_ua):
    """True si el código de unidad administrativa corresponde a una aduana."""
    cd = (cd_ua or "").strip()
    return cd.isdigit() and CD_UA_ADUANA_MIN <= int(cd) <= CD_UA_ADUANA_MAX


def construir_catalogo_previo(movimientos):
    """Deriva la numeración anterior al 2022-07-01 a partir de los propios datos.

    No existe catálogo publicado de la numeración vieja, pero las filas previas
    a la renumeración son internamente consistentes: para cada `un_admin` se
    toma la `desc_larga_un` dominante. Sobre las ~10 000 filas anteriores a esa
    fecha la etiqueta dominante cubre el 98,35 %.
    """
    conteo = defaultdict(lambda: defaultdict(int))
    for mov in movimientos:
        fecha = mov.get("fecha_efectiva")
        if not fecha or fecha >= FECHA_RENUMERACION:
            continue
        codigo = (mov.get("un_admin") or "").strip()
        etiqueta = normalizar_unidad(mov.get("desc_larga_un"))
        if codigo and etiqueta:
            conteo[codigo][etiqueta] += 1

    return {
        codigo: max(etiquetas.items(), key=lambda kv: kv[1])[0]
        for codigo, etiquetas in conteo.items()
    }


def resolver_aduana(mov, catalogo_previo, catalogo_vigente):
    """Devuelve el nombre de la unidad a la que pertenece un movimiento.

    Usa el catálogo de la época de `fecha_efectiva`. Si el código no está en el
    catálogo correspondiente cae a `desc_larga_un` normalizada: pasa con 11
    filas del universo (código "3", una dirección general), y ahí la etiqueta
    cruda es correcta.
    """
    codigo = (mov.get("un_admin") or "").strip()
    fecha = mov.get("fecha_efectiva")
    catalogo = catalogo_vigente if (fecha and fecha >= FECHA_RENUMERACION) else catalogo_previo
    return catalogo.get(codigo) or normalizar_unidad(mov.get("desc_larga_un"))


def _clave_orden(mov):
    """Orden cronológico dentro de la trayectoria de UN empleado.

    `id` va al final solo como desempate estable de último recurso; no aporta
    cronología (dentro de una plaza los ids decrecen), pero en las 922 filas del
    universo nunca llega a usarse porque no hay empates en (fecha, sec).
    """
    return (mov["fecha_efectiva"], mov.get("sec") or 0, mov.get("id") or 0)


def _nombre_completo(mov):
    partes = [mov.get("ap_pat"), mov.get("ap_mat"), mov.get("nombre")]
    return " ".join(p for p in partes if p).strip()


def segmentar_trayectoria(trayectoria, aduana_de, catalogo_puestos=None):
    """Parte la trayectoria de un empleado en gestiones de titularidad.

    Un tramo es una racha contigua de movimientos en el mismo puesto de
    titularidad y la misma aduana. El par TE1 + RE1 del 1 de enero (fin y
    reingreso de nombramiento el mismo día, distinguidos por `sec`) cae dentro
    del mismo tramo y no corta la titularidad.

    `aduana_de` es un callable movimiento -> nombre de unidad.
    """
    gestiones = []
    i = 0
    total = len(trayectoria)

    while i < total:
        if trayectoria[i].get("cd_puesto") not in PUESTOS_TITULARIDAD:
            i += 1
            continue

        aduana = aduana_de(trayectoria[i])
        j = i
        while (
            j + 1 < total
            and trayectoria[j + 1].get("cd_puesto") in PUESTOS_TITULARIDAD
            and aduana_de(trayectoria[j + 1]) == aduana
        ):
            j += 1

        tramo = trayectoria[i:j + 1]
        siguiente = trayectoria[j + 1] if j + 1 < total else None
        gestiones.append(_armar_gestion(aduana, tramo, siguiente,
                                        trayectoria[i - 1] if i > 0 else None,
                                        aduana_de, catalogo_puestos))
        i = j + 1

    return gestiones


def _fila_completa(mov, catalogo_puestos=None):
    """Copia una fila de movimiento tal cual la trajo el SQL, sin las marcas
    internas `_override_mov_pos`/`_un_admin_ok` (ver aplicar_override_mov_pos)
    y con `sal_base` ya convertido a float (Decimal de MySQL) — para que el
    front pueda diffear CAMPO POR CAMPO contra el registro cronológico
    inmediato anterior, igual que hace con el historial completo de un
    empleado (MovimientosPersonalHistorialView), en vez del subconjunto
    reducido que se exponía antes.

    `catalogo_puestos` ({cd_pto_funcional: nombre_puesto_funcional} desde
    CAT_PTO_FUNC, ver RotacionTitularesAduanasView) agrega el nombre del
    puesto funcional del `cd_puesto` de esta fila — el catálogo autoritativo
    de nombres, no `desc_larga_p` (que viene tal cual la capturó ZAFIRO y
    puede venir vacía o desactualizada).
    """
    fila = {k: v for k, v in mov.items() if not k.startswith("_")}
    if fila.get("sal_base") is not None:
        fila["sal_base"] = float(fila["sal_base"])
    if catalogo_puestos is not None:
        fila["nombre_puesto_funcional"] = catalogo_puestos.get((fila.get("cd_puesto") or "").strip())
    return fila


def _armar_gestion(aduana, tramo, siguiente, previo, aduana_de, catalogo_puestos=None):
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
        elif siguiente.get("cd_puesto") in PUESTOS_TITULARIDAD:
            tipo = SALIDA_TRASLADO
        else:
            tipo = SALIDA_OTRO_PUESTO

    origen = None
    if previo is not None:
        if previo.get("cd_puesto") in PUESTOS_TITULARIDAD:
            origen = {"tipo": "ADUANA", "valor": aduana_de(previo)}
        else:
            origen = {"tipo": "PUESTO", "valor": previo.get("cd_puesto")}

    return {
        "aduana": aduana,
        "num_empleado": entrada.get("num_empleado"),
        "nombre": _nombre_completo(entrada),
        "sexo": entrada.get("sexo"),
        "un_admin": (entrada.get("un_admin") or "").strip(),
        "cd_puesto": entrada.get("cd_puesto"),
        "nombre_puesto_funcional": (
            catalogo_puestos.get((entrada.get("cd_puesto") or "").strip())
            if catalogo_puestos is not None else None
        ),
        "nivel_tabular": entrada.get("nivel_tabular"),
        "plaza_entrada": entrada.get("posicion"),
        "plazas": sorted({m.get("posicion") for m in tramo if m.get("posicion")}),
        "fecha_entrada": entrada.get("fecha_efectiva"),
        "entrada_accion": entrada.get("accion"),
        "entrada_accion_nombre": entrada.get("accion_nombre"),
        "entrada_motivo": entrada.get("motivo"),
        "entrada_motivo_nombre": entrada.get("motivo_nombre"),
        "entrada_fecha_captura": entrada.get("fecha_captura"),
        "entrada_por": entrada.get("por"),
        # Fila cruda completa de la entrada (todas las columnas del SQL,
        # ver _trayectorias_de_titulares en views.py) — baseline real para el
        # diff campo por campo del primer movimiento de la gestión.
        "entrada_completo": _fila_completa(entrada, catalogo_puestos),
        "fecha_salida": salida.get("fecha_efectiva") if salida else None,
        "salida_accion": salida.get("accion") if salida else None,
        "salida_accion_nombre": salida.get("accion_nombre") if salida else None,
        "salida_motivo": salida.get("motivo") if salida else None,
        "salida_motivo_nombre": salida.get("motivo_nombre") if salida else None,
        "salida_fecha_captura": salida.get("fecha_captura") if salida else None,
        "salida_por": salida.get("por") if salida else None,
        "salida_destino_unidad": (
            aduana_de(salida) if salida and tipo in (SALIDA_TRASLADO, SALIDA_OTRO_PUESTO) else None
        ),
        "salida_destino_puesto": (
            salida.get("cd_puesto") if salida and tipo == SALIDA_OTRO_PUESTO else None
        ),
        "salida_destino_plaza": (
            salida.get("posicion") if salida and tipo != SALIDA_BAJA else None
        ),
        # Fila cruda completa del movimiento de salida (todas las columnas del
        # SQL) — en SALIDA_PUESTO es la MISMA fila que describe la entrada al
        # nuevo puesto (por construcción, ver nota 3 del encabezado), así que
        # el front puede diffearla campo por campo contra el último movimiento
        # dentro de la aduana y mostrar qué cambió al salir de la titularidad.
        "salida_completo": _fila_completa(salida, catalogo_puestos) if salida else None,
        "tipo_salida": tipo,
        "origen": origen,
        # Fila cruda completa del movimiento previo a la entrada (todas las
        # columnas del SQL) — cuando `origen.tipo == "PUESTO"`, "origen" solo
        # trae el código de puesto; esto le da al front la plaza/UA/depto de
        # donde vino, mismo criterio que `salida_completo` para el destino.
        "origen_completo": _fila_completa(previo, catalogo_puestos) if previo is not None else None,
        "corregida_por_mov_pos": any(m.get("_override_mov_pos") for m in tramo),
        "total_movimientos": len(tramo),
        # Filas completas (todas las columnas), en el mismo orden cronológico
        # (fecha_efectiva, sec) en que las entrega el SQL — ver _fila_completa.
        "movimientos": [_fila_completa(m, catalogo_puestos) for m in tramo[1:]],
    }


def calcular_vacancias(gestiones, hoy):
    """Huecos entre la salida de una gestión y la entrada de la siguiente.

    La última queda abierta si la gestión más reciente de la aduana ya cerró.
    Toda vacancia está anclada a un movimiento de salida y otro de entrada,
    nunca a una ausencia de datos.
    """
    vacancias = []

    for actual, siguiente in zip(gestiones, gestiones[1:]):
        fin = actual["fecha_salida"]
        inicio = siguiente["fecha_entrada"]
        if fin and inicio > fin:
            vacancias.append({
                "desde": fin,
                "hasta": inicio,
                "dias": (inicio - fin).days,
                "sale": actual["nombre"],
                "motivo_salida": actual["salida_motivo_nombre"],
                "tipo_salida": actual["tipo_salida"],
                "entra": siguiente["nombre"],
                "motivo_entrada": siguiente["entrada_motivo_nombre"],
                "abierta": False,
            })

    ultima = gestiones[-1]
    if ultima["tipo_salida"] != SALIDA_ACTIVO and ultima["fecha_salida"]:
        vacancias.append({
            "desde": ultima["fecha_salida"],
            "hasta": None,
            "dias": (hoy - ultima["fecha_salida"]).days,
            "sale": ultima["nombre"],
            "motivo_salida": ultima["salida_motivo_nombre"],
            "tipo_salida": ultima["tipo_salida"],
            "entra": None,
            "motivo_entrada": None,
            "abierta": True,
        })

    return vacancias


def aplicar_override_mov_pos(movimientos, adscripcion_plaza, catalogo_previo, catalogo_vigente):
    """Corrige las filas de personal que se quedaron con el código de unidad
    viejo después de que su plaza ya había sido renumerada.

    `adscripcion_plaza(posicion, fecha)` debe devolver (cd_ua, motivo) según
    MOV_POS, o None si no hay historia previa a esa fecha.

    Solo se corrige cuando el motivo en MOV_POS es una alineación
    organizacional. Un cambio de adscripción real que cae el mismo día que un
    movimiento de personal NO es un error — ver nota 4 del encabezado.

    Muta `movimientos` marcando `_un_admin_ok` y `_override_mov_pos`, y devuelve
    cuántas filas corrigió.
    """
    corregidas = 0

    for mov in movimientos:
        if mov.get("cd_puesto") not in PUESTOS_TITULARIDAD:
            continue

        adscripcion = adscripcion_plaza(mov.get("posicion"), mov.get("fecha_efectiva"))
        if not adscripcion:
            continue

        cd_ua_plaza, motivo_plaza = adscripcion
        if "lineaci" not in (motivo_plaza or "").lower():
            continue

        fecha = mov.get("fecha_efectiva")
        catalogo = catalogo_vigente if (fecha and fecha >= FECHA_RENUMERACION) else catalogo_previo
        unidad_plaza = catalogo.get((cd_ua_plaza or "").strip())
        if not unidad_plaza:
            continue

        if unidad_plaza != resolver_aduana(mov, catalogo_previo, catalogo_vigente):
            mov["_un_admin_ok"] = unidad_plaza
            mov["_override_mov_pos"] = True
            corregidas += 1

    return corregidas


def construir_rotacion(movimientos, catalogo_vigente, hoy,
                       adscripcion_plaza=None, catalogo_puestos=None):
    """Punto de entrada. Devuelve la línea de tiempo agrupada por aduana.

    `movimientos` son TODAS las filas de la trayectoria de cada titular, no solo
    las de los dos puestos de titularidad: el paso 3 necesita el movimiento
    siguiente para fechar la salida, y ese ya está fuera de la aduana.

    `catalogo_vigente` es {cd_ua: unidad_administrativa} desde
    EMPLEADOS_COMPLETOS_SIG. `adscripcion_plaza` es opcional; sin él se omite
    el override de MOV_POS. `catalogo_puestos` es opcional,
    {cd_pto_funcional: nombre_puesto_funcional} desde CAT_PTO_FUNC; sin él se
    omite el nombre de puesto funcional en la respuesta.
    """
    catalogo_previo = construir_catalogo_previo(movimientos)

    # Invertido para resolver el código VIGENTE de cada aduana a partir de su
    # nombre — `codigos_ua` (más abajo) junta TODOS los códigos que la aduana
    # tuvo alguna vez (antes y después de la renumeración del 2022-07-01, ver
    # nota 1 del encabezado) y no tiene orden cronológico, así que mostrarlo
    # tal cual confunde (p. ej. "107 → 183" en Ciudad Reynosa sugiere que 107
    # es el código viejo cuando es al revés). El código actual es simplemente
    # el que el catálogo vigente le asigna hoy a ese nombre.
    reverso_vigente = {nombre: cd_ua for cd_ua, nombre in catalogo_vigente.items()}

    corregidas = 0
    if adscripcion_plaza is not None:
        corregidas = aplicar_override_mov_pos(
            movimientos, adscripcion_plaza, catalogo_previo, catalogo_vigente
        )

    def aduana_de(mov):
        return mov.get("_un_admin_ok") or resolver_aduana(mov, catalogo_previo, catalogo_vigente)

    por_empleado = defaultdict(list)
    for mov in movimientos:
        por_empleado[mov.get("num_empleado")].append(mov)

    gestiones = []
    for trayectoria in por_empleado.values():
        trayectoria.sort(key=_clave_orden)
        gestiones.extend(segmentar_trayectoria(trayectoria, aduana_de, catalogo_puestos))

    por_aduana = defaultdict(list)
    for gestion in gestiones:
        gestion["dias_gestion"] = (
            (gestion["fecha_salida"] or hoy) - gestion["fecha_entrada"]
        ).days
        por_aduana[gestion["aduana"]].append(gestion)

    aduanas = []
    for nombre in sorted(por_aduana):
        propias = sorted(por_aduana[nombre], key=lambda g: g["fecha_entrada"])
        vacancias = calcular_vacancias(propias, hoy)
        titular = next(
            (g for g in propias if g["tipo_salida"] == SALIDA_ACTIVO), None
        )
        aduanas.append({
            "aduana": nombre,
            "aduana_corta": _nombre_corto(nombre),
            "codigos_ua": sorted({g["un_admin"] for g in propias if g["un_admin"]}),
            "codigo_ua_actual": reverso_vigente.get(nombre),
            "plazas": sorted({p for g in propias for p in g["plazas"]}),
            "cd_puestos": sorted({g["cd_puesto"] for g in propias if g["cd_puesto"]}),
            "titular_actual": titular["nombre"] if titular else None,
            "titular_desde": titular["fecha_entrada"] if titular else None,
            "total_gestiones": len(propias),
            "total_vacancias": len(vacancias),
            "dias_acefalia": sum(v["dias"] for v in vacancias),
            "gestiones": propias,
            "vacancias": vacancias,
        })

    return {
        "corte": hoy,
        "total_aduanas": len(aduanas),
        "total_gestiones": len(gestiones),
        "total_titulares": len(por_empleado),
        "filas_corregidas_por_mov_pos": corregidas,
        "aduanas": aduanas,
    }


def _nombre_corto(nombre):
    """"Aduana de Ciudad Juárez con sede en Chihuahua" -> "Ciudad Juárez"."""
    corto = nombre.split(" con sede")[0]
    for prefijo in ("Aduana del ", "Aduana de "):
        if corto.startswith(prefijo):
            corto = corto[len(prefijo):]
            break
    return corto.strip()
