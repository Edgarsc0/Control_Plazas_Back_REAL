# Catálogo de Unidades de Negocio (UN). Copia backend del mismo catálogo que
# vive en el frontend, en Control_De_Plazas_Frontend/src/utils/catalogosUnUa.js
# (UN_CATALOG) — si agregas/quitas una UN, actualiza AMBOS archivos.
#
# No existe una tabla catálogo real: `Cd UN` es una columna de texto en la
# tabla externa EMPLEADOS_COMPLETOS_SIG (recargada completa por el import de
# ZAFIRO), sin FK posible. El backend valida siempre contra esta copia antes
# de guardar un scope — nunca confía en un código que venga del cliente sin
# verificarlo aquí. Una divergencia entre este archivo y el del frontend
# falla cerrado (rechaza el código en el POST/PATCH), no abierto.
UN_CATALOG = {
    "00001": "Agencia Nacional de Aduanas de México",
    "00002": "Órgano Interno de Control",
    "00003": "Dirección General de Evaluación",
    "00004": "Dirección General de Procesamiento Electrónico de Datos Aduaneros",
    "00100": "Dirección General de Operación Aduanera",
    "00200": "Dirección General de Investigación Aduanera",
    "00300": "Dirección General de Atención Aduanera y Asuntos Internacionales",
    "00400": "Dirección General de Modernización, Equipamiento e Infraestructura Aduanera",
    "00500": "Dirección General Jurídica de Aduanas",
    "00600": "Dirección General de Recaudación",
    "00700": "Dirección General de Tecnologías de la Información",
    "00800": "Dirección General de Planeación Aduanera",
    "00900": "Unidad de Administración y Finanzas",
}


def normalizar_cd_un(raw):
    """Limpia un código de UN y lo valida contra el catálogo.

    Devuelve el código normalizado (5 dígitos) o None si no es un código
    reconocido — nunca lanza excepción, para que el llamador decida cómo
    reportar el error (ver GroupSerializer.validate_un_scope).
    """
    if raw is None:
        return None
    codigo = str(raw).strip().zfill(5)
    return codigo if codigo in UN_CATALOG else None
