# Catálogo de Unidades Administrativas (UA) y la Unidad de Negocio (UN) a la
# que pertenece cada una. Copia backend de UA_CATALOG en
# Control_De_Plazas_Frontend/src/utils/catalogosUnUa.js — si agregas/quitas
# una UA, actualiza AMBOS archivos (mismo criterio que un_catalog.py).
#
# La pertenencia UA -> UN se verificó contra EMPLEADOS_COMPLETOS_SIG
# (2026-10-05): 65 códigos, cada uno bajo exactamente una UN. Solo dos UN
# tienen UAs adscritas además de la propia: 00100 (DGOA, 50 aduanas) y 00900
# (UAF, 2 direcciones operativas). En las otras 11 la única UA es la UN misma.
#
# Igual que con la UN, el rol se ancla al CÓDIGO (3 dígitos) y nunca al
# nombre, que es texto libre de ZAFIRO.
UA_CATALOG = {
    "001": ("00001", "Agencia Nacional de Aduanas de México"),
    "002": ("00002", "Órgano Interno de Control"),
    "003": ("00003", "Dirección General de Evaluación"),
    "004": ("00004", "Dirección General de Procesamiento Electrónico de Datos Aduaneros"),
    "100": ("00100", "Dirección General de Operación Aduanera"),
    "101": ("00100", "Aduana de Agua Prieta (Sonora)"),
    "102": ("00100", "Aduana de Ciudad Acuña (Coahuila)"),
    "103": ("00100", "Aduana de Ciudad Camargo (Tamaulipas)"),
    "104": ("00100", "Aduana de Ciudad Hidalgo (Chiapas)"),
    "105": ("00100", "Aduana de Ciudad Juárez (Chihuahua)"),
    "106": ("00100", "Aduana de Ciudad Miguel Alemán (Tamaulipas)"),
    "107": ("00100", "Aduana de Ciudad Reynosa (Tamaulipas)"),
    "108": ("00100", "Aduana de Colombia (Nuevo León)"),
    "109": ("00100", "Aduana de Matamoros (Tamaulipas)"),
    "110": ("00100", "Aduana de Mexicali (Baja California)"),
    "111": ("00100", "Aduana de Naco (Sonora)"),
    "112": ("00100", "Aduana de Nogales (Sonora)"),
    "113": ("00100", "Aduana de Nuevo Laredo (Tamaulipas)"),
    "114": ("00100", "Aduana de Ojinaga (Chihuahua)"),
    "115": ("00100", "Aduana de Piedras Negras (Coahuila)"),
    "116": ("00100", "Aduana de Puerto Palomas (Chihuahua)"),
    "117": ("00100", "Aduana de San Luis Río Colorado (Sonora)"),
    "118": ("00100", "Aduana de Sonoyta (Sonora)"),
    "119": ("00100", "Aduana de Tecate (Baja California)"),
    "120": ("00100", "Aduana de Tijuana (Baja California)"),
    "121": ("00100", "Aduana de Subteniente López (Quintana Roo)"),
    "122": ("00100", "Aduana de Acapulco (Guerrero)"),
    "123": ("00100", "Aduana de Altamira (Tamaulipas)"),
    "124": ("00100", "Aduana de Cancún (Quintana Roo)"),
    "125": ("00100", "Aduana de Ciudad del Carmen (Campeche)"),
    "126": ("00100", "Aduana de Coatzacoalcos (Veracruz)"),
    "127": ("00100", "Aduana de Dos Bocas (Tabasco)"),
    "128": ("00100", "Aduana de Ensenada (Baja California)"),
    "129": ("00100", "Aduana de Guaymas (Sonora)"),
    "130": ("00100", "Aduana de La Paz (Baja California Sur)"),
    "131": ("00100", "Aduana de Lázaro Cárdenas (Michoacán)"),
    "132": ("00100", "Aduana de Manzanillo (Colima)"),
    "133": ("00100", "Aduana de Mazatlán (Sinaloa)"),
    "134": ("00100", "Aduana de Progreso (Yucatán)"),
    "135": ("00100", "Aduana de Salina Cruz (Oaxaca)"),
    "136": ("00100", "Aduana de Tampico (Tamaulipas)"),
    "137": ("00100", "Aduana de Tuxpan (Veracruz)"),
    "138": ("00100", "Aduana de Veracruz (Veracruz)"),
    "139": ("00100", "Aduana AICM (Ciudad de México)"),
    "140": ("00100", "Aduana Aeropuerto Felipe Ángeles (Estado de México)"),
    "141": ("00100", "Aduana de Aguascalientes (Aguascalientes)"),
    "142": ("00100", "Aduana de Chihuahua (Chihuahua)"),
    "143": ("00100", "Aduana de Guadalajara (Jalisco)"),
    "144": ("00100", "Aduana de Guanajuato (Guanajuato)"),
    "145": ("00100", "Aduana de Monterrey (Nuevo León)"),
    "146": ("00100", "Aduana de Puebla (Puebla)"),
    "147": ("00100", "Aduana de Querétaro (Querétaro)"),
    "148": ("00100", "Aduana de Toluca (Estado de México)"),
    "149": ("00100", "Aduana de Torreón (Coahuila)"),
    "150": ("00100", "Aduana de México (Ciudad de México)"),
    "200": ("00200", "Dirección General de Investigación Aduanera"),
    "300": ("00300", "Dirección General de Atención Aduanera y Asuntos Internacionales"),
    "400": ("00400", "Dirección General de Modernización, Equipamiento e Infraestructura Aduanera"),
    "500": ("00500", "Dirección General Jurídica de Aduanas"),
    "600": ("00600", "Dirección General de Recaudación"),
    "700": ("00700", "Dirección General de Tecnologías de la Información"),
    "800": ("00800", "Dirección General de Planeación Aduanera"),
    "900": ("00900", "Unidad de Administración y Finanzas"),
    "909": ("00900", "Dirección Operativa de Administración y Finanzas (CDMX)"),
    "922": ("00900", "Dirección Operativa de Administración y Finanzas (Chichimequillas, Qro.)"),
}


def normalizar_cd_ua(raw):
    """Limpia un código de UA y lo valida contra el catálogo. Devuelve el
    código normalizado (3 dígitos) o None si no es reconocido."""
    if raw is None:
        return None
    codigo = str(raw).strip().zfill(3)
    return codigo if codigo in UA_CATALOG else None


def un_de_ua(cd_ua):
    """Código de la UN a la que pertenece la UA (None si no existe)."""
    entrada = UA_CATALOG.get(cd_ua)
    return entrada[0] if entrada else None


def nombre_ua(cd_ua):
    entrada = UA_CATALOG.get(cd_ua)
    return entrada[1] if entrada else None


def ua_propia_de_un(cd_un):
    """La UA "cabeza" de una UN: la que representa a la unidad misma (ej.
    00100 -> "100", 00004 -> "004"). Las demás UAs de esa UN son las
    adscritas (aduanas, direcciones operativas)."""
    return str(int(cd_un)).zfill(3)


def uas_adscritas(cd_un):
    """UAs de la UN que NO son la unidad misma, ordenadas por nombre."""
    propia = ua_propia_de_un(cd_un)
    return sorted(
        (codigo for codigo, (un, _) in UA_CATALOG.items() if un == cd_un and codigo != propia),
        key=lambda codigo: UA_CATALOG[codigo][1],
    )


# Unidades de Negocio cuyo rol titular puede tener un alcance distinto al de
# su propia unidad (incluido "sin restricción"). La 00001 es la oficina del
# titular de la ANAM: su equipo consulta la plantilla de toda la Agencia.
UN_TITULAR_ALCANCE_LIBRE = frozenset({"00001"})


def titular_con_alcance_libre(cd_un, cd_ua):
    """True si el titular de esa unidad puede cambiar su alcance por UN."""
    return not cd_ua and str(cd_un or "").strip() in UN_TITULAR_ALCANCE_LIBRE
