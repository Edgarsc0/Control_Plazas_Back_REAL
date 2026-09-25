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


# Códigos que aparecen en los datos pero NO son unidades de negocio propias:
# son variantes históricas de una del catálogo. Las unidades generales son y
# seguirán siendo 13, así que estos no se agregan a UN_CATALOG (no se pueden
# elegir al configurar un rol) — solo se suman al conjunto contra el que se
# compara al filtrar, para que las filas viejas no se queden huérfanas.
#
#   "00005" -> "00004" (DGPEDA). Confirmado con el usuario sobre las 18 bajas
#   que lo traen (todas de 2022-2023). No existe ni una sola fila con este
#   código en la plantilla activa: solo sobrevive en BAJAS_SIG (18) y en
#   MOV_POS (1,144).
#   "00011" -> "00100" (Dirección General de Operación Aduanera). Confirmado
#   por el usuario revisando los movimientos que lo traen (3 filas en
#   cp_tbl_mov_completo, 17 en MOV_POS).
#
# Estos dos son los ÚNICOS códigos fuera de catálogo que aparecen en los datos:
# auditadas las tres tablas con UN (EMPLEADOS_COMPLETOS_SIG, BAJAS_SIG, MOV_POS
# y cp_tbl_mov_completo), todo lo demás cae en las 13 unidades generales.
UN_ALIAS = {
    "00005": "00004",
    "00011": "00100",
}


def expandir_alias_un(codigos):
    """Añade a un scope los códigos variantes que equivalen a sus unidades.

    Se usa SOLO al comparar contra los datos, nunca al guardar: RolUnScope
    sigue almacenando únicamente códigos del catálogo, así que la
    configuración de un rol se lee tal cual se eligió.
    """
    if codigos is None:
        return None
    permitidos = set(codigos)
    permitidos.update(
        variante for variante, canonico in UN_ALIAS.items() if canonico in permitidos
    )
    return sorted(permitidos)
