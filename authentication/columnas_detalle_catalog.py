# Catálogo de columnas de la tabla "Plantilla Detalle". Copia backend del
# mismo catálogo que vive en el frontend, en
# Control_De_Plazas_Frontend/src/config/plantillaDetalleColumns.js — si
# agregas/quitas una columna, actualiza AMBOS archivos.
#
# Se usa para (a) validar qué claves puede elegir un admin al restringir un
# rol (RolColumnScope) y (b) el set fijo de columnas que SIEMPRE viajan sin
# importar la restricción, porque varias funciones de la UI (foto, edición
# de celdas, badges de estatus) las necesitan para operar. No incluye "foto"
# (columna presentacional, no es un campo de datos — su visibilidad ya la
# controla el permiso view_plantilla_detalle_foto).
COLUMNAS_DETALLE_CATALOGO = {
    "posicion", "estado_plaza", "fecha_vacancia", "fecha_ocupacion", "estado_nomina",
    "solicitante", "nombre_candidato", "motivo_solicitud", "id_empleado", "rfc", "curp",
    "nombres", "motivo", "fecha_efectiva_personal", "fecha_de_captura", "qna",
    "fecha_prevista_de_salida", "nj", "codigo_presupuestal", "nivel", "escala", "smb", "smn",
    "partida", "tipo_de_contratacion", "cd_un", "unidad_de_negocio", "cd_ua",
    "unidad_administrativa", "cd_pto_funcional", "nombre_puesto_funcional", "id_departamento",
    "departamento", "dependencia_directa", "codigo", "entidad_federativa", "tipo_de_aduana",
    "ubicacion", "descripcion_ubicacion", "tipo_de_personal_sedena_semar", "rango",
    "fecha_de_ingreso", "dg_o_aduana_compactada", "fecha_anuencia_detalle",
    "oficios_autorizacion_shcp", "plazas_eventuales_autorizacion_2026", "candidato",
    "reportada", "fecha_genera_vacante", "cap_anual", "cap_mensual",
    "observaciones_plantillas_do", "observaciones_proyectos_alineaciones", "anno_vacancia",
    "id_field", "numeral", "ua", "cent", "dir", "subd", "jd", "depto", "aduana", "id_tipo",
    "tipo", "estado", "municipio", "latitud", "longitud", "ua2", "observaciones",
    "posicion_civil_sedena_semar", "personal_militar_o_civil", "val_estat", "val_estatx",
    "status_jefe_inm_posicion", "numempleado", "sindicato", "estado_en_nomina",
    "ua_validacion", "validando_posicion_por_documento", "nj_comp", "nj_ok", "columna",
    "nombre_nj", "nj_operativo_comb", "proyecto_2024_reduccion_plazas_eventuales",
    "salario_base_mov",
}

# Identificadores/status que varias funciones de la UI necesitan para operar
# sin importar qué columnas eligió el admin — no son "columnas" que se
# puedan restringir, son plumbing interno (ver investigación previa: foto,
# edición de celdas, VacanciaDetalleModal, badge de estatus). Ninguno de
# estos es un dato sensible por sí solo (son códigos/identificadores, no
# nombre/RFC/salario). Varias de estas claves también las inyecta el backend
# en tiempo de enriquecimiento y no existen en el catálogo de arriba
# (mov_pos_id, val_estat, marca_no_disponible, fecha_anuencia_detalle_override).
COLUMNAS_DETALLE_SIEMPRE_INCLUIDAS = {
    "posicion", "numempleado", "id_empleado", "mov_pos_id",
    "estado_nomina", "val_estat", "marca_no_disponible",
    "fecha_anuencia_detalle_override", "partida",
}


def normalizar_columna_detalle(raw):
    """Valida una clave de columna contra el catálogo. Devuelve la clave tal
    cual si es válida, o None si no se reconoce — nunca lanza excepción."""
    if raw is None:
        return None
    clave = str(raw).strip()
    return clave if clave in COLUMNAS_DETALLE_CATALOGO else None
