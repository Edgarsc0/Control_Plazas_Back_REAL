from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.functions import Trim


class PlantillaVacantesPorNivel(models.Model):
    posición = models.CharField(
        db_column="Posición", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    estado_nomina = models.CharField(
        db_column="Estado Nomina", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    num_empleado = models.CharField(
        db_column="Num Empleado", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    rfc = models.CharField(
        db_column="RFC", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    curp = models.CharField(
        db_column="CURP", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    nombres = models.CharField(
        db_column="Nombres", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    motivo = models.CharField(
        db_column="Motivo", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    fecha_efectiva_personal_field = models.CharField(
        db_column="Fecha efectiva (Personal)", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    fecha_de_captura = models.CharField(
        db_column="Fecha de captura", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    qna_field = models.CharField(
        db_column="Qna#", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    fecha_prevista_de_salida = models.CharField(
        db_column="Fecha prevista de salida", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nj = models.CharField(
        db_column="NJ", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    código_presupuestal = models.CharField(
        db_column="Código Presupuestal", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nivel = models.CharField(
        db_column="Nivel", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    escala = models.CharField(
        db_column="Escala", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    smb = models.CharField(
        db_column="SMB", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    smn = models.CharField(
        db_column="SMN", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    partida = models.CharField(
        db_column="Partida", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    cd_un = models.CharField(
        db_column="Cd UN", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    unidad_de_negocio = models.CharField(
        db_column="Unidad de Negocio", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cd_ua = models.CharField(
        db_column="Cd UA", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    unidad_administrativa = models.CharField(
        db_column="Unidad Administrativa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cd_pto_funcional = models.CharField(
        db_column="Cd Pto Funcional", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_puesto_funcional = models.CharField(
        db_column="Nombre Puesto Funcional", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    id_departamento = models.CharField(
        db_column="Id Departamento", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    departamento = models.CharField(
        db_column="Departamento", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    dependencia_directa = models.CharField(
        db_column="Dependencia Directa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    observaciones = models.CharField(
        db_column="Observaciones", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    programa = models.CharField(
        db_column="Programa", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    num_empleado1 = models.CharField(
        db_column="Num empleado1", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    posición1 = models.CharField(
        db_column="Posición1", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    especialidad = models.CharField(
        db_column="Especialidad", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    entidad_federativa = models.CharField(
        db_column="Entidad Federativa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tipo_de_aduana = models.CharField(
        db_column="Tipo de Aduana", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    ubicación = models.CharField(
        db_column="Ubicación", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    descripción_ubicación = models.CharField(
        db_column="Descripción ubicación", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    posición_civil_sedena_semar = models.CharField(
        db_column="Posición _Civil / SEDENA / SEMAR",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    personal_militar_o_civil = models.CharField(
        db_column="Personal Militar o Civil", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tipo_de_personal_sedena_semar = models.CharField(
        db_column="Tipo de personal SEDENA / SEMAR",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    rango = models.CharField(
        db_column="Rango", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    fecha_de_ingreso = models.CharField(
        db_column="Fecha de ingreso", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    dg_o_aduana_compactada = models.CharField(
        db_column="DG o Aduana compactada", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    depuración_vacancia = models.CharField(
        db_column="Depuración Vacancia", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    proyecto_2025_337_plazas_para_autorización_shcp = models.CharField(
        db_column="Proyecto 2025 337 plazas para autorización SHCP",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    plazas_eventuales_registradas_para_autorización_2026 = models.CharField(
        db_column="Plazas eventuales registradas para autorización 2026",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    candidato = models.CharField(
        db_column="Candidato", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    validandoposición_por_estatus = models.CharField(
        db_column="Validandoposición por estatus", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    reportada_validación_estructura_2026 = models.CharField(
        db_column="Reportada Validación Estructura 2026",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    fecha_que_se_genera_la_vacante = models.CharField(
        db_column="Fecha que se genera la vacante",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cap_anual = models.CharField(
        db_column="CAP ANUAL", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cap_mensual = models.CharField(
        db_column="CAP MENSUAL", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = "PLANTILLA_VACANTES_POR_NIVEL"


class PlantillaQuincenal(models.Model):
    posición = models.CharField(
        db_column="Posición", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    estado_nomina = models.CharField(
        db_column="Estado Nomina", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    num_empleado = models.CharField(
        db_column="Num Empleado", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    rfc = models.CharField(
        db_column="RFC", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    curp = models.CharField(
        db_column="CURP", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    nombres = models.CharField(
        db_column="Nombres", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    motivo = models.CharField(
        db_column="Motivo", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    fecha_efectiva_personal_field = models.CharField(
        db_column="Fecha efectiva (Personal)", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    fecha_de_captura = models.CharField(
        db_column="Fecha de captura", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    qna_field = models.CharField(
        db_column="Qna#", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters. Field renamed because it ended with '_'.
    fecha_prevista_de_salida = models.CharField(
        db_column="Fecha prevista de salida", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nj = models.CharField(
        db_column="NJ", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    código_presupuestal = models.CharField(
        db_column="Código Presupuestal", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nivel = models.CharField(
        db_column="Nivel", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    escala = models.CharField(
        db_column="Escala", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    smb = models.CharField(
        db_column="SMB", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    smn = models.CharField(
        db_column="SMN", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    partida = models.CharField(
        db_column="Partida", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    tipo_de_contratacion = models.CharField(max_length=255, blank=True, null=True)
    cd_un = models.CharField(
        db_column="Cd UN", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    unidad_de_negocio = models.CharField(
        db_column="Unidad de Negocio", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cd_ua = models.CharField(
        db_column="Cd UA", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    unidad_administrativa = models.CharField(
        db_column="Unidad Administrativa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cd_pto_funcional = models.CharField(
        db_column="Cd Pto Funcional", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    nombre_puesto_funcional = models.CharField(
        db_column="Nombre Puesto Funcional", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    id_departamento = models.CharField(
        db_column="Id Departamento", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    departamento = models.CharField(
        db_column="Departamento", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    dependencia_directa = models.CharField(
        db_column="Dependencia Directa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    observaciones = models.CharField(
        db_column="Observaciones", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    programa = models.CharField(
        db_column="Programa", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    num_empleado1 = models.CharField(
        db_column="Num empleado1", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    posición1 = models.CharField(
        db_column="Posición1", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    especialidad = models.CharField(
        db_column="Especialidad", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    entidad_federativa = models.CharField(
        db_column="Entidad Federativa", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tipo_de_aduana = models.CharField(
        db_column="Tipo de Aduana", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    ubicación = models.CharField(
        db_column="Ubicación", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    descripción_ubicación = models.CharField(
        db_column="Descripción ubicación", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    posición_civil_sedena_semar = models.CharField(
        db_column="Posición _Civil / SEDENA / SEMAR",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    personal_militar_o_civil = models.CharField(
        db_column="Personal Militar o Civil", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    tipo_de_personal_sedena_semar = models.CharField(
        db_column="Tipo de personal SEDENA / SEMAR",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    rango = models.CharField(
        db_column="Rango", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    fecha_de_ingreso = models.CharField(
        db_column="Fecha de ingreso", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    dg_o_aduana_compactada = models.CharField(
        db_column="DG o Aduana compactada", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    depuración_vacancia = models.CharField(
        db_column="Depuración Vacancia", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    proyecto_2025_337_plazas_para_autorización_shcp = models.CharField(
        db_column="Proyecto 2025 337 plazas para autorización SHCP",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    plazas_eventuales_registradas_para_autorización_2026 = models.CharField(
        db_column="Plazas eventuales registradas para autorización 2026",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    candidato = models.CharField(
        db_column="Candidato", max_length=255, blank=True, null=True
    )  # Field name made lowercase.
    validandoposición_por_estatus = models.CharField(
        db_column="Validandoposición por estatus", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    reportada_validación_estructura_2026 = models.CharField(
        db_column="Reportada Validación Estructura 2026",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    fecha_que_se_genera_la_vacante = models.CharField(
        db_column="Fecha que se genera la vacante",
        max_length=255,
        blank=True,
        null=True,
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cap_anual = models.CharField(
        db_column="CAP ANUAL", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.
    cap_mensual = models.CharField(
        db_column="CAP MENSUAL", max_length=255, blank=True, null=True
    )  # Field name made lowercase. Field renamed to remove unsuitable characters.

    class Meta:
        managed = False
        db_table = "plantilla_quincenal"


class Plantilla1800Plazas(models.Model):
    """Modelo para la tabla plantilla_1800_plazas"""

    posición = models.CharField(db_column="Posición", max_length=255, blank=True, null=True)
    estado_nómina = models.CharField(db_column="Estado Nómina", max_length=255, blank=True, null=True)
    num_empleado = models.CharField(db_column="Num Empleado", max_length=255, blank=True, null=True)
    estado_posición = models.CharField(db_column="Estado posición", max_length=255, blank=True, null=True)
    rfc = models.CharField(db_column="RFC", max_length=255, blank=True, null=True)
    curp = models.CharField(db_column="CURP", max_length=255, blank=True, null=True)
    nombres = models.CharField(db_column="Nombres", max_length=255, blank=True, null=True)
    motivo = models.CharField(db_column="Motivo", max_length=255, blank=True, null=True)
    fecha_efectiva_personal = models.CharField(db_column="Fecha efectiva (Personal)", max_length=255, blank=True, null=True)
    fecha_de_captura = models.CharField(db_column="Fecha de captura", max_length=255, blank=True, null=True)
    qna = models.CharField(db_column="Qna#", max_length=255, blank=True, null=True)
    fecha_prevista_de_salida = models.CharField(db_column="Fecha prevista de salida", max_length=255, blank=True, null=True)
    código_presupuestal = models.CharField(db_column="Código Presupuestal", max_length=255, blank=True, null=True)
    nj = models.CharField(db_column="NJ", max_length=255, blank=True, null=True)
    nivel = models.CharField(db_column="Nivel", max_length=255, blank=True, null=True)
    escala = models.CharField(db_column="Escala", max_length=255, blank=True, null=True)
    smb = models.CharField(db_column="SMB", max_length=255, blank=True, null=True)
    smn = models.CharField(db_column="SMN", max_length=255, blank=True, null=True)
    partida = models.CharField(db_column="Partida", max_length=255, blank=True, null=True)
    tipo_de_contratación = models.CharField(db_column="Tipo de Contratación", max_length=255, blank=True, null=True)
    cd_un = models.CharField(db_column="Cd UN", max_length=255, blank=True, null=True)
    unidad_de_negocio = models.CharField(db_column="Unidad de Negocio", max_length=255, blank=True, null=True)
    cd_ua = models.CharField(db_column="Cd UA", max_length=255, blank=True, null=True)
    unidad_administrativa = models.CharField(db_column="Unidad Administrativa", max_length=255, blank=True, null=True)
    cd_pto_funcional_asignado = models.CharField(db_column="Cd Pto Funcional asignado", max_length=255, blank=True, null=True)
    nombre_puesto_funcional_asignado = models.CharField(db_column="Nombre Puesto Funcional Asignado", max_length=255, blank=True, null=True)
    id_departamento = models.CharField(db_column="Id Departamento", max_length=255, blank=True, null=True)
    departamento = models.CharField(db_column="Departamento", max_length=255, blank=True, null=True)
    dependencia_directa = models.CharField(db_column="Dependencia Directa", max_length=255, blank=True, null=True)
    of_de_solicitud = models.CharField(db_column="Of. De Solicitud", max_length=255, blank=True, null=True)
    ipe = models.CharField(db_column="IPE", max_length=255, blank=True, null=True)
    entidad_federativa = models.CharField(db_column="Entidad Federativa", max_length=255, blank=True, null=True)
    tipo_de_aduana = models.CharField(db_column="Tipo de Aduana", max_length=255, blank=True, null=True)
    ubicación = models.CharField(db_column="Ubicación", max_length=255, blank=True, null=True)
    descripción_ubicación = models.CharField(db_column="Descripción ubicación", max_length=255, blank=True, null=True)
    personal_militar_o_civil = models.CharField(db_column="Personal Militar o Civil", max_length=255, blank=True, null=True)
    tipo_de_personal_sedena_semar = models.CharField(db_column="Tipo de personal SEDENA / SEMAR", max_length=255, blank=True, null=True)
    rango = models.CharField(db_column="Rango", max_length=255, blank=True, null=True)
    formato_de_compatibiliddad = models.CharField(db_column="Formato de compatibiliddad", max_length=255, blank=True, null=True)
    fecha_de_ingreso = models.CharField(db_column="Fecha de ingreso", max_length=255, blank=True, null=True)
    f_de_vacancia = models.CharField(db_column="F. de Vacancia", max_length=255, blank=True, null=True)
    of_shcp = models.CharField(db_column="Of. SHCP", max_length=255, blank=True, null=True)
    observaciones = models.CharField(db_column="Observaciones", max_length=255, blank=True, null=True)
    cap_anual = models.CharField(db_column="CAP ANUAL", max_length=255, blank=True, null=True)
    cap_mensual = models.CharField(db_column="CAP MENSUAL", max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = "plantilla_1800_plazas"
        indexes = [
            models.Index(fields=["of_de_solicitud", "nivel"], name="idx_p1800_ofsol_niv"),
            models.Index(fields=["nivel"], name="idx_p1800_nivel"),
        ]

    def __str__(self):
        return f"Plantilla 1800 - {self.num_empleado} ({self.nombres})"


class EmpleadosCompletosSigBase(models.Model):
    """
    Modelo para la tabla EMPLEADOS_COMPLETOS_SIG.
    Se importa automáticamente vía tarea Celery desde el CSV de ZAFIRO (id=6).
    Celery trunca y recarga esta tabla en cada ejecución.
    """

    id_field = models.CharField(
        db_column="Id_campo", max_length=2, blank=True, null=True
    )
    numeral = models.CharField(db_column="numeral", max_length=6, blank=True, null=True)
    ua = models.CharField(db_column="ua", max_length=255, blank=True, null=True)
    cent = models.CharField(db_column="cent", max_length=1, blank=True, null=True)
    dir = models.CharField(db_column="dir", max_length=2, blank=True, null=True)
    subd = models.CharField(db_column="subd", max_length=1, blank=True, null=True)
    jd = models.CharField(db_column="jd", max_length=1, blank=True, null=True)
    depto = models.CharField(db_column="depto", max_length=11, blank=True, null=True)
    aduana = models.CharField(db_column="Aduana", max_length=90, blank=True, null=True)
    id_tipo = models.CharField(
        db_column="id tipo", max_length=1, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    tipo = models.CharField(db_column="tipo", max_length=19, blank=True, null=True)
    estado = models.CharField(db_column="estado", max_length=255, blank=True, null=True)
    municipio = models.CharField(
        db_column="municipio", max_length=255, blank=True, null=True
    )
    latitud = models.CharField(
        db_column="latitud", max_length=12, blank=True, null=True
    )
    longitud = models.CharField(
        db_column="longitud", max_length=13, blank=True, null=True
    )
    ua2 = models.CharField(db_column="ua2", max_length=255, blank=True, null=True)
    posicion = models.CharField(
        db_column="Posición", max_length=8, blank=True, null=True, db_index=True
    )  # Field renamed to remove unsuitable characters.
    estado_nomina = models.CharField(
        db_column="Estado Nómina", max_length=1, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    id_empleado = models.CharField(
        db_column="Id Empleado", max_length=10, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    rfc = models.CharField(db_column="RFC", max_length=13, blank=True, null=True)
    curp = models.CharField(db_column="CURP", max_length=18, blank=True, null=True)
    nombres = models.CharField(
        db_column="Nombres", max_length=44, blank=True, null=True
    )
    motivo = models.CharField(db_column="Motivo", max_length=30, blank=True, null=True)
    fecha_efectiva_personal = models.CharField(
        db_column="Fecha efectiva (Personal)", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    fecha_de_captura = models.CharField(
        db_column="Fecha de captura", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    qna = models.CharField(db_column="Qna", max_length=255, blank=True, null=True)
    fecha_prevista_de_salida = models.CharField(
        db_column="Fecha prevista de salida", max_length=10, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    nj = models.CharField(db_column="NJ", max_length=255, blank=True, null=True)
    codigo_presupuestal = models.CharField(
        db_column="Código Presupuestal", max_length=10, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    nivel = models.CharField(db_column="Nivel", max_length=4, blank=True, null=True)
    escala = models.CharField(db_column="Escala", max_length=255, blank=True, null=True)
    smb = models.CharField(db_column="SMB", max_length=8, blank=True, null=True)
    smn = models.CharField(db_column="SMN", max_length=9, blank=True, null=True)
    partida = models.CharField(
        db_column="Partida", max_length=255, blank=True, null=True
    )
    tipo_de_contratacion = models.CharField(
        db_column="TIPO DE CONTRATACIÓN", max_length=8, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    cd_un = models.CharField(
        db_column="Cd UN", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    unidad_de_negocio = models.CharField(
        db_column="Unidad de Negocio", max_length=74, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    cd_ua = models.CharField(
        db_column="Cd UA", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    unidad_administrativa = models.CharField(
        db_column="Unidad Administrativa", max_length=90, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    cd_pto_funcional = models.CharField(
        db_column="Cd Pto Funcional", max_length=6, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    nombre_puesto_funcional = models.CharField(
        db_column="Nombre Puesto Funcional", max_length=123, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    id_departamento = models.CharField(
        db_column="Id Departamento", max_length=11, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    departamento = models.CharField(
        db_column="Departamento", max_length=90, blank=True, null=True
    )
    dependencia_directa = models.CharField(
        db_column="DependenciaDirecta", max_length=255, blank=True, null=True
    )
    observaciones = models.CharField(
        db_column="OBSERVACIONES", max_length=100, blank=True, null=True
    )
    ubicacion = models.CharField(
        db_column="Ubicación", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    descripcion_ubicacion = models.CharField(
        db_column="Descripción ubicación", max_length=30, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    posicion_civil_sedena_semar = models.CharField(
        db_column="Posición _Civil / SEDENA / SEMAR",
        max_length=22,
        blank=True,
        null=True,
    )  # Field renamed to remove unsuitable characters.
    personal_militar_o_civil = models.CharField(
        db_column="Personal Militar o Civil", max_length=12, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    tipo_de_personal_sedena_semar = models.CharField(
        db_column="Tipo de personal SEDENA / SEMAR",
        max_length=11,
        blank=True,
        null=True,
    )  # Field renamed to remove unsuitable characters.
    rango = models.CharField(db_column="Rango", max_length=28, blank=True, null=True)
    fecha_de_ingreso = models.CharField(
        db_column="Fecha de ingreso", max_length=10, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    val_estat = models.CharField(
        db_column="Val_estat", max_length=7, blank=True, null=True
    )
    status_jefe_inm_posicion = models.CharField(
        db_column="Status Jefe Inm Posición", max_length=9, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    numempleado = models.CharField(
        db_column="Numempleado", max_length=10, blank=True, null=True
    )
    sindicato = models.CharField(
        db_column="Sindicato", max_length=255, blank=True, null=True
    )
    entidad_federativa = models.CharField(
        db_column="Entidad Federativa", max_length=19, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    tipo_de_aduana = models.CharField(
        db_column="Tipo de Aduana", max_length=10, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    dg_o_aduana_compactada = models.CharField(
        db_column="DG o Aduana compactada", max_length=21, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    proyecto_2024_reduccion_plazas_eventuales = models.CharField(
        db_column="Proyecto 2024 Reducción de plazas Eventuales",
        max_length=100,
        blank=True,
        null=True,
    )  # Field renamed to remove unsuitable characters.
    estado_en_nomina = models.CharField(
        db_column="Estado en nomina", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    ua_validacion = models.CharField(
        db_column="UA Validación", max_length=100, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    validando_posicion_por_documento = models.CharField(
        db_column="Validando de posición por documento",
        max_length=255,
        blank=True,
        null=True,
    )  # Field renamed to remove unsuitable characters.
    val_estatx = models.CharField(
        db_column="Val_estatx", max_length=7, blank=True, null=True
    )
    nj_comp = models.CharField(
        db_column="NJ COMP", max_length=21, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    nj_ok = models.CharField(
        db_column="NJ OK", max_length=255, blank=True, null=True
    )  # Field renamed to remove unsuitable characters.
    columna = models.CharField(
        db_column="Columna", max_length=40, blank=True, null=True
    )
    nombre_nj = models.CharField(
        db_column="nombreNJ", max_length=19, blank=True, null=True
    )
    nj_operativo_comb = models.CharField(
        db_column="NJOperativoComb", max_length=13, blank=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.nombres} ({self.id_empleado})"


class BajasSigBase(models.Model):
    """
    Modelo para la tabla BAJAS_SIG.
    Se importa automáticamente vía tarea Celery desde el CSV de ZAFIRO (id=3).
    Celery trunca y recarga esta tabla en cada ejecución.
    """

    posicion = models.CharField(
        db_column="POSICION", max_length=255, blank=True, null=True
    )
    no_empleado = models.CharField(
        db_column="NO_EMPLEADO", max_length=255, blank=True, null=True
    )
    nombre_completo = models.CharField(
        db_column="NOMBRE_COMPLETO", max_length=255, blank=True, null=True
    )
    primer_apellido = models.CharField(
        db_column="PRIMER_APELLIDO", max_length=255, blank=True, null=True
    )
    segundo_apellido = models.CharField(
        db_column="SEGUNDO_APELLIDO", max_length=255, blank=True, null=True
    )
    accion = models.CharField(db_column="ACCION", max_length=255, blank=True, null=True)
    accion_descr = models.CharField(
        db_column="ACCION_DESCR", max_length=255, blank=True, null=True
    )
    motivo = models.CharField(db_column="MOTIVO", max_length=255, blank=True, null=True)
    motivo_descr = models.CharField(
        db_column="MOTIVO_DESCR", max_length=255, blank=True, null=True
    )
    fecha_efectiva = models.CharField(
        db_column="FECHA_EFECTIVA", max_length=255, blank=True, null=True
    )
    sequencia_efectiva = models.CharField(
        db_column="SEQUENCIA_EFECTIVA", max_length=255, blank=True, null=True
    )
    fecha_aplicacion = models.CharField(
        db_column="FECHA_APLICACION", max_length=255, blank=True, null=True
    )
    humanos_status = models.CharField(
        db_column="HUMANOS_STATUS", max_length=255, blank=True, null=True
    )
    nomina_status = models.CharField(
        db_column="NOMINA_STATUS", max_length=255, blank=True, null=True
    )
    partida = models.CharField(
        db_column="PARTIDA", max_length=255, blank=True, null=True
    )
    unidad_general = models.CharField(
        db_column="UNIDAD_GENERAL", max_length=255, blank=True, null=True
    )
    unidad_admon = models.CharField(
        db_column="UNIDAD_ADMON", max_length=255, blank=True, null=True
    )
    departamento = models.CharField(
        db_column="DEPARTAMENTO", max_length=255, blank=True, null=True
    )
    dependencia_directa = models.CharField(
        db_column="DEPENDENCIA_DIRECTA", max_length=255, blank=True, null=True
    )
    plan_salarial = models.CharField(
        db_column="PLAN_SALARIAL", max_length=255, blank=True, null=True
    )
    grado = models.CharField(db_column="GRADO", max_length=255, blank=True, null=True)
    escala = models.CharField(db_column="ESCALA", max_length=255, blank=True, null=True)
    puesto_presupuestal = models.CharField(
        db_column="PUESTO_PRESUPUESTAL", max_length=255, blank=True, null=True
    )
    nivel_tabular = models.CharField(
        db_column="NIVEL_TABULAR", max_length=255, blank=True, null=True
    )
    grupo_de_pago = models.CharField(
        db_column="GRUPO_DE_PAGO", max_length=255, blank=True, null=True
    )
    beneficios = models.CharField(
        db_column="BENEFICIOS", max_length=255, blank=True, null=True
    )
    smb = models.CharField(db_column="SMB", max_length=255, blank=True, null=True)
    puesto = models.CharField(db_column="PUESTO", max_length=255, blank=True, null=True)
    ubicacion = models.CharField(
        db_column="UBICACION", max_length=255, blank=True, null=True
    )
    inmueble = models.CharField(
        db_column="INMUEBLE", max_length=255, blank=True, null=True
    )
    fecha_prevista = models.CharField(
        db_column="FECHA_PREVISTA", max_length=255, blank=True, null=True
    )
    ultima_actualizacion = models.CharField(
        db_column="ULTIMA_ACTUALIZACION", max_length=255, blank=True, null=True
    )
    ultimo_operador = models.CharField(
        db_column="ULTIMO_OPERADOR", max_length=255, blank=True, null=True
    )
    ultima_fecha_ingreso = models.CharField(
        db_column="ULTIMA_FECHA_INGRESO", max_length=255, blank=True, null=True
    )
    fecha_ingreso = models.CharField(
        db_column="FECHA_INGRESO", max_length=255, blank=True, null=True
    )
    grupo_trabajo = models.CharField(
        db_column="GRUPO_TRABAJO", max_length=255, blank=True, null=True
    )
    codigo_grupo = models.CharField(
        db_column="CODIGO_GRUPO", max_length=255, blank=True, null=True
    )
    fecha_asignacion = models.CharField(
        db_column="FECHA_ASIGNACION", max_length=255, blank=True, null=True
    )
    rfc = models.CharField(db_column="RFC", max_length=255, blank=True, null=True)
    curp = models.CharField(db_column="CURP", max_length=255, blank=True, null=True)
    id_persona = models.CharField(
        db_column="ID_PERSONA", max_length=255, blank=True, null=True
    )
    nivel = models.CharField(db_column="NIVEL", max_length=255, blank=True, null=True)
    nivel1 = models.CharField(db_column="NIVEL1", max_length=255, blank=True, null=True)
    unidad_administrativa = models.CharField(
        db_column="UNIDAD_ADMINISTRATIVA", max_length=255, blank=True, null=True
    )
    genero = models.CharField(db_column="GENERO", max_length=255, blank=True, null=True)
    fecha_entrada_posicion = models.CharField(
        db_column="FECHA_ENTRADA_POSICION", max_length=255, blank=True, null=True
    )
    fecha_posicion = models.CharField(
        db_column="FECHA_POSICION", max_length=255, blank=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.nombre_completo} ({self.no_empleado})"


class MovPosBase(models.Model):
    """
    Modelo para la tabla MOV_POS.
    """

    no_pos_actual = models.CharField(
        db_column="Nº Pos Actual", max_length=255, blank=True, null=True, db_index=True
    )
    f_efva = models.CharField(db_column="F Efva", max_length=255, blank=True, null=True)
    estado_psn = models.CharField(
        db_column="Estado Psn", max_length=255, blank=True, null=True, db_index=True
    )
    fecha_captura = models.CharField(
        db_column="Fecha Captura", max_length=255, blank=True, null=True
    )
    fecha_vacancia = models.CharField(
        db_column="FECHA VACANCIA", max_length=255, blank=True, null=True
    )
    cd_motivo = models.CharField(
        db_column="Cd Motivo", max_length=255, blank=True, null=True
    )
    motivo = models.CharField(db_column="Motivo", max_length=255, blank=True, null=True)
    cd_un = models.CharField(db_column="Cd UN", max_length=255, blank=True, null=True)
    unidad_de_negocio = models.CharField(
        db_column="Unidad de Negocio", max_length=255, blank=True, null=True
    )
    unidad_adva = models.CharField(
        db_column="Unidad Adva#", max_length=255, blank=True, null=True
    )
    cd_departamento = models.CharField(
        db_column="Cd Departamento", max_length=255, blank=True, null=True
    )
    cd_puesto = models.CharField(
        db_column="Cd Puesto", max_length=255, blank=True, null=True
    )
    estado_ptal = models.CharField(
        db_column="Estado Ptal", max_length=255, blank=True, null=True
    )
    fecha_est = models.CharField(
        db_column="Fecha Est", max_length=255, blank=True, null=True
    )
    maximo = models.CharField(db_column="Máximo", max_length=255, blank=True, null=True)
    depnd_drt = models.CharField(
        db_column="Depnd Drt", max_length=255, blank=True, null=True
    )
    depnd_indrt = models.CharField(
        db_column="Depnd Indrt", max_length=255, blank=True, null=True
    )
    ubicacion = models.CharField(
        db_column="Ubicación", max_length=255, blank=True, null=True
    )
    nvl_direc = models.CharField(
        db_column="Nvl Direc", max_length=255, blank=True, null=True
    )
    plan_sal = models.CharField(
        db_column="Plan Sal", max_length=255, blank=True, null=True
    )
    grado = models.CharField(db_column="Grado", max_length=255, blank=True, null=True)
    esc = models.CharField(db_column="Esc", max_length=255, blank=True, null=True)
    puesto_ptal = models.CharField(
        db_column="Puesto Ptal", max_length=255, blank=True, null=True
    )
    partida_ptal = models.CharField(
        db_column="Partida Ptal", max_length=255, blank=True, null=True
    )
    gp_pago = models.CharField(
        db_column="Gp Pago", max_length=255, blank=True, null=True
    )
    prog_beneficios = models.CharField(
        db_column="Prog Beneficios", max_length=255, blank=True, null=True
    )
    fh_ult_actz = models.CharField(
        db_column="F/H Últ Actz", max_length=255, blank=True, null=True
    )
    por = models.CharField(db_column="Por", max_length=255, blank=True, null=True)
    hr_estd_semn = models.CharField(
        db_column="Hr Estd/Semn", max_length=255, blank=True, null=True
    )
    descr = models.CharField(db_column="Descr", max_length=255, blank=True, null=True)
    gp_trabajo = models.CharField(
        db_column="Gp Trabajo", max_length=255, blank=True, null=True
    )
    org_code = models.CharField(
        db_column="Org Code", max_length=255, blank=True, null=True
    )
    grupo_cd_sal = models.CharField(
        db_column="Grupo Cd Sal", max_length=255, blank=True, null=True
    )
    formal_desc = models.CharField(
        db_column="FormalDesc", max_length=255, blank=True, null=True
    )
    pto_compt = models.CharField(
        db_column="Pto Compt", max_length=255, blank=True, null=True
    )
    posn_clv = models.CharField(
        db_column="Posn Clv", max_length=255, blank=True, null=True
    )
    presupuesto = models.CharField(
        db_column="Presupuesto", max_length=255, blank=True, null=True
    )
    nombre_puesto = models.CharField(
        db_column="Nombre Puesto", max_length=255, blank=True, null=True
    )
    categoria_vacancia = models.CharField(
        db_column="CATEGORIA_VACANCIA", max_length=255, blank=True, null=True
    )
    id_registro_desicivo = models.BigIntegerField(
        db_column="idRegistroDesicivo", blank=True, null=True
    )
    tuvo_insubsistencia = models.CharField(
        db_column="TUVO_INSUBSISTENCIA", max_length=1, blank=True, null=True, default="N"
    )
    id_insubsistencia_detectada = models.BigIntegerField(
        db_column="idInsubsistenciaDetectada", blank=True, null=True
    )
    fecha_ocupacion = models.DateField(
        db_column="FECHA_OCUPACION", blank=True, null=True
    )
    id_registro_des_fecha_ocupacion = models.BigIntegerField(
        db_column="ID_REGISTRO_DES_FECHA_OCUPACION", blank=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.no_pos_actual} - {self.nombre_puesto}"


class CatPtoFunc(models.Model):
    """
    Modelo para la tabla CAT_PTO_FUNC.
    """

    cd_pto_funcional = models.CharField(
        db_column="Cd Pto Funcional", max_length=255, blank=True, null=True
    )
    nombre_puesto_funcional = models.CharField(
        db_column="Nombre Puesto Funcional", max_length=255, blank=True, null=True
    )
    cd_norm = models.CharField(
        db_column="CdNorm", max_length=255, blank=True, null=True
    )
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "CAT_PTO_FUNC"

    def __str__(self):
        return f"{self.cd_pto_funcional} - {self.nombre_puesto_funcional}"


class CatAcciones(models.Model):
    """
    Catálogo action -> action_description/descripcion. Adoptada vía
    SeparateDatabaseAndState (la tabla ya existía en producción, poblada
    por el pipeline ZAFIRO). CRUD con auditoría en CatAccionesViewSet.
    """

    action = models.CharField(primary_key=True, max_length=50)
    action_description = models.CharField(max_length=255, blank=True, null=True)
    effective_status = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "cat_acciones"

    def __str__(self):
        return f"{self.action} - {self.action_description}"


class CatAccionesMotivos(models.Model):
    """
    Catálogo accion+cd_motivo -> descripcion/descripcion_larga. Adoptada vía
    SeparateDatabaseAndState (tabla ya existente en producción).
    """

    id = models.AutoField(primary_key=True)
    accion = models.CharField(max_length=10)
    cd_motivo = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=255)
    estado_efectivo = models.CharField(max_length=20)
    descripcion_larga = models.TextField(blank=True, null=True)
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "cat_acciones_motivos"

    def __str__(self):
        return f"{self.accion} - {self.cd_motivo}"


class RcCatCodPresupuestal(models.Model):
    """
    Catálogo de niveles/escalas presupuestales (SMB/SMN por código+escala).
    Pk compuesta real en BD (codigo_presupuestal, escala); adoptada vía
    SeparateDatabaseAndState. Usada por los SPs de post-proceso de ZAFIRO
    (`sp_corregir_smb_smn_empleados`, `sp_llenar_niveles_vacios_pos_activas`).
    """

    pk = models.CompositePrimaryKey("codigo_presupuestal", "escala")
    codigo_presupuestal = models.CharField(max_length=55)
    escala = models.SmallIntegerField()
    nivel = models.CharField(max_length=55, blank=True, null=True)
    smb = models.DecimalField(max_digits=55, decimal_places=2, blank=True, null=True)
    smn = models.DecimalField(max_digits=55, decimal_places=2, blank=True, null=True)
    nivel_jerarquico = models.CharField(max_length=55, blank=True, null=True)
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "rc_cat_cod_presupuestal"

    def __str__(self):
        return f"{self.codigo_presupuestal} - {self.escala}"


class OrganigramaAnam(models.Model):
    """
    Catálogo de estructura organizacional (unidad_negocio/departamento →
    descripción, nivel de dirección, DOAF, posiciones de gerente/director).
    Adoptada vía SeparateDatabaseAndState (tabla ya existente en producción,
    poblada por el pipeline ZAFIRO). Usada por organigrama_tree.build_tree y
    las vistas de búsqueda de organigrama en views.py.

    Contiene DOS conjuntos de filas distinguidos por `isSIGInfo`: el
    institucional/editable (isSIGInfo=False, antes tabla única con
    `departamento` como PK) y el snapshot SIG de solo lectura (isSIGInfo=True,
    antes en la tabla aparte ORGANIGRAMA_ANAM_SIG, fusionada aquí). Como un
    mismo `departamento` puede existir en ambos conjuntos, la PK ya no puede
    ser `departamento`: ahora es `id` autoincremental, con `departamento`
    único solo DENTRO de cada conjunto (unique_together con isSIGInfo). Todo
    lookup por `departamento` debe ir siempre acompañado de un filtro por
    isSIGInfo para no toparse con MultipleObjectsReturned.
    """

    id = models.BigAutoField(primary_key=True)
    departamento = models.CharField(max_length=255)
    unidad_negocio = models.CharField(max_length=255)
    estado_fecha_efectiva = models.CharField(max_length=255)
    descripcion_larga = models.CharField(max_length=500)
    nivel_direccion = models.CharField(max_length=255, blank=True, null=True)
    unidad_administrativa = models.CharField(max_length=255)
    doaf = models.CharField(max_length=255)
    num_posicion_gerente = models.CharField(max_length=255)
    posicion_director = models.CharField(max_length=255)
    subordinados = models.TextField(
        blank=True, null=True,
        help_text="Códigos de departamento (subordinados directos) separados por coma, "
                   "calculados con la misma lógica de organigrama_tree.build_parent_map.",
    )
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)
    isSIGInfo = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = "ORGANIGRAMA_ANAM"
        constraints = [
            models.UniqueConstraint(
                fields=["departamento", "isSIGInfo"],
                name="uq_departamento_sig",
            ),
        ]

    def __str__(self):
        return f"{self.departamento} - {self.descripcion_larga}"


class OrganigramaAnamSig(models.Model):
    """
    Foto fija (snapshot) de ORGANIGRAMA_ANAM tomada el 2026-07-17 — usada
    EXCLUSIVAMENTE por Vista SIG (organigrama-tree/?vista=sig) para que sea
    100% inmune a cualquier edición manual hecha en Vista Institucional
    (estructura, orden Y contenido). Antes, ambas vistas leían la misma fila
    de ORGANIGRAMA_ANAM (filtrada por `isSIGInfo`), lo que dejaba filtrar
    ediciones de contenido hechas desde Institucional.

    No hay pipeline vivo que la resincronice (a diferencia de
    EMPLEADOS_COMPLETOS_SIG/MOV_POS_LATEST, que sí se re-truncan en cada
    import ZAFIRO) — para refrescar esta foto en el futuro, volver a correr
    el management command `congelar_organigrama_sig`.

    Sin `subordinados`: Vista SIG siempre recalcula la estructura en vivo
    desde el determinante (`forzar_recalculo=True`), nunca la lee de una
    columna editable — ver organigrama_tree.build_tree.
    """
    departamento = models.CharField(primary_key=True, max_length=255)
    descripcion_larga = models.CharField(max_length=500)
    nivel_direccion = models.CharField(max_length=255, blank=True, null=True)
    unidad_negocio = models.CharField(max_length=255)
    unidad_administrativa = models.CharField(max_length=255)
    doaf = models.CharField(max_length=255)
    num_posicion_gerente = models.CharField(max_length=255)
    posicion_director = models.CharField(max_length=255)

    class Meta:
        db_table = "ORGANIGRAMA_ANAM_SIG"

    def __str__(self):
        return f"{self.departamento} - {self.descripcion_larga}"


# Enum de negocio (NJ, Descripción). Nivel 3 tiene 2 descripciones válidas
# ("Director" / "Titular de Aduana"), por eso la descripción -no el nivel- es
# la clave única del enum: `nivel_jerarquico` se deriva de ella en save().
NIVELES_JERARQUICOS = (
    (0, "Titular de la Agencia Nacional de Aduanas de México"),
    (1, "Director General"),
    (2, "Director Central"),
    (3, "Director"),
    (3, "Titular de Aduana"),
    (4, "Subdirector"),
    (5, "Jefe de Departamento"),
    (6, "Enlace"),
    (7, "Operativo de Confianza"),
    (8, "Operativo de Base"),
)
NIVEL_JERARQUICO_POR_DESCRIPCION = {descripcion: nivel for nivel, descripcion in NIVELES_JERARQUICOS}
DESCRIPCION_NJ_CHOICES = [(descripcion, f"{nivel} — {descripcion}") for nivel, descripcion in NIVELES_JERARQUICOS]

# Convención corta ya usada por ZAFIRO en las columnas NJ de EMPLEADOS_COMPLETOS_SIG.
# Verificada contra datos reales de producción; nivel 0 no tiene precedente (sin
# empleados hoy en ese nivel).
#
# Nivel 3 es especial: por default es "Director", pero si el "Nombre Puesto
# Funcional" del empleado empieza con "Administrador de Aduana" es "Titular de
# Aduana" (mismo nivel jerárquico 3, sólo cambia la etiqueta) — ver
# `NIVEL_JERARQUICO_LABELS_NIVEL_3_TITULAR_ADUANA` y
# `nivel_jerarquico_sync.aplicar_nivel_a_plazas`.
NIVEL_JERARQUICO_LABELS = {
    0: {"nj": "0", "nj_comp": "0 Titular ANAM", "nj_ok": "0 TITULAR ANAM", "nombre_nj": "TITULAR ANAM", "nj_operativo_comb": "TITULAR ANAM"},
    1: {"nj": "1", "nj_comp": "1 Director General", "nj_ok": "1 DIRECTOR GENERAL", "nombre_nj": "DIRECTOR GENERAL", "nj_operativo_comb": "DIRECTOR GENERAL"},
    2: {"nj": "2", "nj_comp": "2 Director Central", "nj_ok": "2 DIRECTOR CENTRAL", "nombre_nj": "DIRECTOR CENTRAL", "nj_operativo_comb": "DIRECTOR CENTRAL"},
    3: {"nj": "3", "nj_comp": "3 Director", "nj_ok": "3 DIRECTOR", "nombre_nj": "DIRECTOR", "nj_operativo_comb": "DIRECTOR"},
    4: {"nj": "4", "nj_comp": "4 Subdirector", "nj_ok": "4 SUBDIRECTOR", "nombre_nj": "SUBDIRECTOR", "nj_operativo_comb": "SUBDIRECTOR"},
    5: {"nj": "5", "nj_comp": "5 Jefe de Depto", "nj_ok": "5 JEFE DE DEPTO", "nombre_nj": "JEFE DE DEPTO", "nj_operativo_comb": "JEFE DE DEPTO"},
    6: {"nj": "6", "nj_comp": "6 Enlace", "nj_ok": "6 ENLACE", "nombre_nj": "ENLACE", "nj_operativo_comb": "ENLACE"},
    7: {"nj": "7", "nj_comp": "7 Operativo Confianza", "nj_ok": "7 OPERATIVO CONFIANZA", "nombre_nj": "OPERATIVO CONFIANZA", "nj_operativo_comb": "OPERATIVOS"},
    8: {"nj": "8", "nj_comp": "8 Operativo Base", "nj_ok": "8 OPERATIVO BASE", "nombre_nj": "OPERATIVO BASE", "nj_operativo_comb": "OPERATIVOS"},
}

# Variante de nivel 3 cuando el "Nombre Puesto Funcional" del empleado empieza
# con "Administrador de Aduana": mismo nivel jerárquico (3), pero etiqueta
# "Titular de Aduana" en vez de "Director". Ver `NIVELES_JERARQUICOS` arriba.
NIVEL_3_PREFIJO_TITULAR_ADUANA = "Administrador de Aduana"
NIVEL_JERARQUICO_LABELS_NIVEL_3_TITULAR_ADUANA = {
    "nj": "3", "nj_comp": "3 Titular de Aduana", "nj_ok": "3 TITULAR DE ADUANA",
    "nombre_nj": "TITULAR DE ADUANA", "nj_operativo_comb": "TITULAR DE ADUANA",
}

FUENTE_PRIORIDAD_CHOICES = [
    ("nivel_jerarquico", "Nivel Jerárquico (asignación manual)"),
    ("nvl_direc_origen", "Nvl Direc (referencia MOV_POS)"),
]


class NivelJerarquicoPrioridadConfig(models.Model):
    """
    Config singleton (pk=1): cuál columna de cat_nivel_jerarquico_plaza manda
    como fuente de verdad del nivel jerárquico al cruzar contra MOV_POS y
    EMPLEADOS_COMPLETOS_SIG (checkbox de prioridad en el frontend). Se
    reaplica automáticamente en cada import ZAFIRO (ver
    plantilla.tasks._reaplicar_prioridad_nivel_jerarquico) porque esas dos
    tablas se truncan y recargan completas cada 30 min.
    """

    fuente = models.CharField(max_length=20, choices=FUENTE_PRIORIDAD_CHOICES, blank=True, null=True)
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "cat_nivel_jerarquico_prioridad"

    def __str__(self):
        return self.fuente or "sin prioridad"


class CatNivelJerarquicoPlaza(models.Model):
    """
    Nivel jerárquico (enum NJ + descripción) asignado manualmente por plaza.
    Se siembra/actualiza desde MOV_POS (plaza + Nvl Direc de referencia) en
    cada import ZAFIRO (ver
    `plantilla.tasks._sincronizar_plazas_nivel_jerarquico`); el nivel
    jerárquico se asigna después en bloque desde el frontend (`bulk-assign`)
    y no viene de ninguna fuente automática.
    """

    plaza = models.CharField(max_length=255, primary_key=True)
    nivel_jerarquico = models.SmallIntegerField(blank=True, null=True, editable=False)
    descripcion_nivel_jerarquico = models.CharField(
        max_length=255, blank=True, null=True, choices=DESCRIPCION_NJ_CHOICES
    )
    nvl_direc_origen = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Referencia informativa: valor de 'Nvl Direc' en MOV_POS al momento de sincronizar.",
    )
    modificado_por = models.CharField(max_length=255, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True, auto_now=True)

    class Meta:
        managed = True
        db_table = "cat_nivel_jerarquico_plaza"

    def save(self, *args, **kwargs):
        self.nivel_jerarquico = NIVEL_JERARQUICO_POR_DESCRIPCION.get(self.descripcion_nivel_jerarquico)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plaza} - {self.descripcion_nivel_jerarquico or 'sin asignar'}"


# Columnas admitidas en cat_correccion_posicion. Añadir aquí una nueva key es
# suficiente para habilitarla (sin migración) — ver CatCorreccionPosicion.
COLUMNAS_CORRECCION_VALIDAS = {"codigo", "tipo_de_aduana", "dg_o_aduana_compactada"}


class CatCorreccionPosicion(models.Model):
    """
    Catálogo clave-valor por posición para que la plantilla del sistema
    (EMPLEADOS_COMPLETOS_SIG) coincida con la plantilla del Excel de
    referencia (``plantilla_con_columna_codigo.xlsx``) en columnas donde
    ZAFIRO trae un valor incompleto, vacío o distinto — "Código" (ZAFIRO
    nunca lo trae), "Tipo de Aduana"/"DG o Aduana compactada" (~33% vienen
    vacíos en ZAFIRO pero el Excel siempre los trae). Se carga inicialmente
    con `cargar_correcciones_plantilla` y a partir de ahí se corrige a mano
    desde el tab "Catálogos" (ej. cuando una posición se realinea a otra
    unidad y hay que actualizar su aduana) — ver CatCorreccionPosicionListView/
    DetailView, que pivotan esta tabla clave-valor a un renglón por posición.

    IMPORTANTE — separación deliberada de `TblColumnasPlantillaQuincenal`:
    esta tabla es un catálogo simple (última edición gana, sin historial),
    para "corrección automática de datos" que se edita ocasionalmente. Las
    columnas AL–AV (candidato, reportada, CAP anual, etc.) son justo lo
    opuesto — captura manual constante con auditoría completa vía
    CeldaOverride (valor_original + historial de cada cambio) — por eso
    viven en su propia tabla y no comparten mecanismo.

    Diseño clave-valor: agregar una columna nueva en el futuro no requiere
    migración de BD, solo declarar la key en COLUMNAS_CORRECCION_VALIDAS.
    """

    posicion = models.CharField(max_length=20, db_index=True)
    columna = models.CharField(max_length=100)  # key de COLUMNAS_CORRECCION_VALIDAS
    valor = models.TextField(blank=True, null=True)
    modificado_por = models.CharField(max_length=150, blank=True, null=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "cat_correccion_posicion"
        unique_together = [("posicion", "columna")]
        indexes = [
            models.Index(fields=["posicion"]),
        ]

    def __str__(self):
        return f"{self.posicion} · {self.columna} = {self.valor!r}"


class GeocodeCache(models.Model):
    """
    Tabla-hash dirección normalizada -> coordenadas, para no volver a llamar
    a Nominatim (ni a reconstruir el mapeo escaneando toda EMPLEADOS_COMPLETOS_SIG)
    en cada corrida de `importar_zafiro` (cada 30 min). Ver
    `plantilla.tasks._geocodificar_empleados_sin_coordenadas`: cada corrida
    primero busca aquí por `direccion` (clave, ya limpiada/normalizada) y solo
    pega a la API externa las direcciones que de verdad son nuevas — que
    entonces se insertan aquí para la siguiente corrida.
    """

    direccion = models.CharField(max_length=255, unique=True, db_index=True)
    latitud = models.CharField(max_length=12)
    longitud = models.CharField(max_length=13)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "GEOCODE_CACHE"

    def __str__(self):
        return f"{self.direccion} -> ({self.latitud}, {self.longitud})"


class EmpleadosCompletosSig(EmpleadosCompletosSigBase):
    class Meta:
        managed = True
        db_table = "EMPLEADOS_COMPLETOS_SIG"
        indexes = [
            models.Index(fields=["nivel"], name="idx_emp_nivel"),
            models.Index(fields=["estado_nomina"], name="idx_emp_estnom"),
            # Índices de expresión: las views filtran con Trim(col); un índice
            # plano no se usaría, uno funcional sobre TRIM(col) sí.
            models.Index(Trim("nivel"), name="idx_emp_t_nivel"),
            models.Index(Trim("estado_nomina"), name="idx_emp_t_estnom"),
        ]


class EmpleadosCompletosSigHistorico(EmpleadosCompletosSigBase):
    fecha_descarga = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "EMPLEADOS_COMPLETOS_SIG_HISTORICO"


class BajasSig(BajasSigBase):
    class Meta:
        managed = True
        db_table = "BAJAS_SIG"
        indexes = [
            models.Index(fields=["posicion"], name="idx_baj_posicion"),
            models.Index(fields=["fecha_efectiva"], name="idx_baj_fefec"),
            models.Index(Trim("motivo_descr"), name="idx_baj_t_motdes"),
            models.Index(Trim("accion_descr"), name="idx_baj_t_accdes"),
        ]


class BajasSigHistorico(BajasSigBase):
    fecha_descarga = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "BAJAS_SIG_HISTORICO"


class MovPos(MovPosBase):
    class Meta:
        managed = True
        db_table = "MOV_POS"
        indexes = [
            models.Index(fields=["f_efva", "fecha_captura"], name="idx_movpos_fefva_fcap"),
            models.Index(Trim("estado_psn"), name="idx_mp_t_estpsn"),
            models.Index(Trim("motivo"), name="idx_mp_t_motivo"),
            models.Index(Trim("unidad_adva"), name="idx_mp_t_unidadv"),
        ]


class MovPosLatest(models.Model):
    """
    Una fila por `Nº Pos Actual` con el registro más reciente de MOV_POS
    (mismo criterio que la window function ROW_NUMBER() OVER que antes se
    recalculaba en cada request en 6+ endpoints, ver AUDITORIA_BUGS_BACK.md
    BE2). La tarea de importación de ZAFIRO la reconstruye una vez al
    final de cada swap Blue-Green; los endpoints solo hacen lookup indexado.
    """

    no_pos_actual = models.CharField(
        db_column="Nº Pos Actual", max_length=255, primary_key=True
    )
    mov_pos_id = models.BigIntegerField(db_column="id")
    estado_psn = models.CharField(
        db_column="Estado Psn", max_length=255, blank=True, null=True, db_index=True
    )

    class Meta:
        managed = True
        db_table = "MOV_POS_LATEST"


class MovPosHistorico(MovPosBase):
    fecha_descarga = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "MOV_POS_HISTORICO"


class EmpleadosCompletosSigStaging(EmpleadosCompletosSigBase):
    class Meta:
        managed = True
        db_table = "EMPLEADOS_COMPLETOS_SIG_STAGING"
        # Mismos índices que la tabla principal: el sync hace swap Blue-Green
        # (RENAME staging<->main), así que la staging debe traerlos para que la
        # main viva nunca quede sin índices.
        indexes = [
            models.Index(fields=["nivel"], name="idx_emps_nivel"),
            models.Index(fields=["estado_nomina"], name="idx_emps_estnom"),
            models.Index(Trim("nivel"), name="idx_emps_t_nivel"),
            models.Index(Trim("estado_nomina"), name="idx_emps_t_estnom"),
        ]


class BajasSigStaging(BajasSigBase):
    class Meta:
        managed = True
        db_table = "BAJAS_SIG_STAGING"
        indexes = [
            models.Index(fields=["posicion"], name="idx_bajs_posicion"),
            models.Index(fields=["fecha_efectiva"], name="idx_bajs_fefec"),
            models.Index(Trim("motivo_descr"), name="idx_bajs_t_motdes"),
            models.Index(Trim("accion_descr"), name="idx_bajs_t_accdes"),
        ]


class MovPosStaging(MovPosBase):
    class Meta:
        managed = True
        db_table = "MOV_POS_STAGING"
        indexes = [
            models.Index(fields=["f_efva", "fecha_captura"], name="idx_mps_fefva_fcap"),
            models.Index(Trim("estado_psn"), name="idx_mps_t_estpsn"),
            models.Index(Trim("motivo"), name="idx_mps_t_motivo"),
            models.Index(Trim("unidad_adva"), name="idx_mps_t_unidadv"),
        ]


class DatosPersonalesBase(models.Model):
    """
    Modelo para la tabla DATOS_PERSONALES.
    Se importa automáticamente vía tarea Celery desde el CSV de ZAFIRO
    (zafiro_info, argIndex por definir). Celery trunca y recarga esta tabla
    en cada ejecución. Todas las columnas son varchar(255) (esquema fuente:
    zafiro_info.csv, delimitado por "|").
    """

    no_empleado = models.CharField(
        db_column="NO_EMPLEADO", max_length=255, blank=True, null=True, db_index=True
    )
    hr_id_persona = models.CharField(
        db_column="HR_ID_PERSONA", max_length=255, blank=True, null=True
    )
    position_nbr = models.CharField(
        db_column="POSITION_NBR", max_length=255, blank=True, null=True
    )
    nombre_completo = models.CharField(
        db_column="NOMBRE_COMPLETO", max_length=255, blank=True, null=True
    )
    rfc = models.CharField(db_column="RFC", max_length=255, blank=True, null=True)
    curp = models.CharField(db_column="CURP", max_length=255, blank=True, null=True)
    puesto_estructural = models.CharField(
        db_column="PUESTO_ESTRUCTURAL", max_length=255, blank=True, null=True
    )
    puesto_funcional = models.CharField(
        db_column="PUESTO_FUNCIONAL", max_length=255, blank=True, null=True
    )
    puesto = models.CharField(db_column="PUESTO", max_length=255, blank=True, null=True)
    escolaridad_tipo = models.CharField(
        db_column="ESCOLARIDAD_TIPO", max_length=255, blank=True, null=True
    )
    escolaridad_nivrl = models.CharField(
        db_column="ESCOLARIDAD_NIVRL", max_length=255, blank=True, null=True
    )
    escolaridad_area = models.CharField(
        db_column="ESCOLARIDAD_AREA", max_length=255, blank=True, null=True
    )
    carrera = models.CharField(
        db_column="CARRERA", max_length=255, blank=True, null=True
    )
    centro_escolar = models.CharField(
        db_column="CENTRO_ESCOLAR", max_length=255, blank=True, null=True
    )
    humanos_status = models.CharField(
        db_column="HUMANOS_STATUS", max_length=255, blank=True, null=True
    )
    estatus_nomina = models.CharField(
        db_column="ESTATUS_NOMINA", max_length=255, blank=True, null=True
    )
    phone = models.CharField(db_column="PHONE", max_length=255, blank=True, null=True)
    phone1 = models.CharField(
        db_column="PHONE1", max_length=255, blank=True, null=True
    )
    calle = models.CharField(db_column="CALLE", max_length=255, blank=True, null=True)
    hr_numero_exterior = models.CharField(
        db_column="HR_NUMERO_EXTERIOR", max_length=255, blank=True, null=True
    )
    hr_numero_interior = models.CharField(
        db_column="HR_NUMERO_INTERIOR", max_length=255, blank=True, null=True
    )
    postal = models.CharField(
        db_column="POSTAL", max_length=255, blank=True, null=True
    )
    colonia = models.CharField(
        db_column="COLONIA", max_length=255, blank=True, null=True
    )
    hr_municipio = models.CharField(
        db_column="HR_MUNICIPIO", max_length=255, blank=True, null=True
    )
    estado = models.CharField(
        db_column="ESTADO", max_length=255, blank=True, null=True
    )
    email_addr2 = models.CharField(
        db_column="EMAIL_ADDR2", max_length=255, blank=True, null=True
    )
    email_addr = models.CharField(
        db_column="EMAIL_ADDR", max_length=255, blank=True, null=True
    )
    deptid = models.CharField(
        db_column="DEPTID", max_length=255, blank=True, null=True
    )
    unidad_administrativa = models.CharField(
        db_column="UNIDAD_ADMINISTRATIVA", max_length=255, blank=True, null=True
    )
    # No vienen en el CSV fuente: columnas extra solicitadas, quedan NULL en
    # la importación automática de Celery (llenado manual vía CeldaOverride,
    # ver plantilla.celda_override.registrar_y_aplicar_override_datos_personales).
    # `extension` es JSON porque algunas personas cubren varias áreas/módulos
    # con extensión propia cada una: valor simple (string) si solo tiene una,
    # o lista `[{"extension": "...", "area": "..."}, ...]` si tiene varias
    # (ver Directorio ANAM, personas como "Luis Ernesto Sena Hernandez" en
    # Nuevo Laredo con 14 extensiones distintas, una por módulo).
    extension = models.JSONField(
        db_column="extension", blank=True, null=True
    )
    conmutador = models.CharField(
        db_column="Conmutador", max_length=255, blank=True, null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.nombre_completo} ({self.no_empleado})"


class DatosPersonales(DatosPersonalesBase):
    class Meta:
        managed = True
        db_table = "DATOS_PERSONALES"


class DatosPersonalesHistorico(DatosPersonalesBase):
    fecha_descarga = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = "DATOS_PERSONALES_HISTORICO"


class DatosPersonalesStaging(DatosPersonalesBase):
    class Meta:
        managed = True
        db_table = "DATOS_PERSONALES_STAGING"


class ZafiroBitacora(models.Model):
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    duracion_segundos = models.FloatField(null=True, blank=True)
    registros_posiciones = models.IntegerField(default=0)
    registros_completos = models.IntegerField(default=0)
    registros_bajas = models.IntegerField(default=0)
    registros_historial = models.IntegerField(default=0)
    registros_datos_personales = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="OK")
    error_message = models.TextField(null=True, blank=True)
    es_historico = models.BooleanField(default=False)
    logs_en_vivo = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = "ZAFIRO_BITACORA"
        ordering = ["-fecha_ejecucion"]

    def __str__(self):
        return f"{self.fecha_ejecucion} - {self.status}"


class AlineacionOrganizacionalHistorico(models.Model):
    """1 fila por día con el % de Alineación General (ver
    `get_mov_pos_alineacion_stats` en plantilla/views.py) al momento en que
    corrió la última importación ZAFIRO de ese día. Se actualiza (upsert por
    `fecha`) al final de cada corrida de `importar_zafiro` en plantilla/tasks.py
    solo si el valor cambió respecto al ya guardado, para tener un histórico
    diario y poder graficar la tendencia en AlineacionOrganizacionalTab."""

    fecha = models.DateField(unique=True)
    porcentaje_alineacion_general = models.DecimalField(max_digits=5, decimal_places=1)
    total_activas = models.IntegerField(default=0)
    total_alineadas = models.IntegerField(default=0)
    total_con_diferencias = models.IntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "ALINEACION_ORGANIZACIONAL_HISTORICO"
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.porcentaje_alineacion_general}%"


class CpTblMovCompleto290526Base(models.Model):
    id = models.AutoField(primary_key=True)
    posicion = models.CharField(max_length=50, blank=True, null=True)
    num_empleado = models.CharField(max_length=20, blank=True, null=True)
    columna_c = models.CharField(
        db_column="columna_C", max_length=100, blank=True, null=True
    )  # Field name made lowercase.
    columna_d = models.CharField(
        db_column="columna_D", max_length=100, blank=True, null=True
    )  # Field name made lowercase.
    nombre = models.CharField(max_length=100, blank=True, null=True)
    ap_pat = models.CharField(max_length=100, blank=True, null=True)
    ap_mat = models.CharField(max_length=100, blank=True, null=True)
    accion = models.CharField(max_length=50, blank=True, null=True)
    accion_nombre = models.CharField(max_length=100, blank=True, null=True)
    motivo = models.CharField(max_length=50, blank=True, null=True)
    motivo_nombre = models.CharField(max_length=100, blank=True, null=True)
    fecha_efectiva = models.DateField(blank=True, null=True)
    sec = models.IntegerField(blank=True, null=True)
    fecha_captura = models.DateField(blank=True, null=True)
    est_hr = models.CharField(max_length=50, blank=True, null=True)
    estado_pago = models.CharField(max_length=50, blank=True, null=True)
    partida_presup = models.CharField(max_length=50, blank=True, null=True)
    un = models.CharField(max_length=50, blank=True, null=True)
    un_admin = models.CharField(max_length=100, blank=True, null=True)
    id_depto = models.CharField(max_length=50, blank=True, null=True)
    depen_direc = models.CharField(max_length=100, blank=True, null=True)
    plan_sal = models.CharField(max_length=50, blank=True, null=True)
    grado = models.CharField(max_length=50, blank=True, null=True)
    escala = models.CharField(max_length=50, blank=True, null=True)
    puesto_ptal = models.CharField(max_length=100, blank=True, null=True)
    nivel_tabular = models.CharField(max_length=50, blank=True, null=True)
    gp_pago = models.CharField(max_length=50, blank=True, null=True)
    prog_benef = models.CharField(max_length=100, blank=True, null=True)
    sal_base = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    cd_puesto = models.CharField(max_length=50, blank=True, null=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    id_estbl = models.CharField(max_length=50, blank=True, null=True)
    salida_prevista = models.DateField(blank=True, null=True)
    fecha_ult_actz = models.DateTimeField(blank=True, null=True)
    por = models.CharField(max_length=50, blank=True, null=True)
    ult_inicio = models.DateField(blank=True, null=True)
    fecha_inicial = models.DateField(blank=True, null=True)
    gp_trabajo = models.CharField(max_length=100, blank=True, null=True)
    grupo_cd_sal = models.CharField(max_length=50, blank=True, null=True)
    antiguo_empr = models.IntegerField(blank=True, null=True)
    rfc = models.CharField(max_length=13, blank=True, null=True)
    curp = models.CharField(max_length=18, blank=True, null=True)
    id_persona = models.CharField(max_length=50, blank=True, null=True)
    desc_larga_p = models.TextField(blank=True, null=True)
    nv_jerarquico = models.CharField(max_length=50, blank=True, null=True)
    desc_larga_un = models.TextField(blank=True, null=True)
    sexo = models.CharField(max_length=20, blank=True, null=True)
    fecha_entrada = models.DateField(blank=True, null=True)
    fecha_posicion = models.DateField(blank=True, null=True)

    class Meta:
        abstract = True

class CpTblMovCompleto290526(CpTblMovCompleto290526Base):
    class Meta:
        managed = False
        db_table = "cp_tbl_mov_completo_29_05_26"

class CpTblMovCompleto290526Staging(CpTblMovCompleto290526Base):
    class Meta:
        managed = False
        db_table = "cp_tbl_mov_completo_29_05_26_staging"

class CpTblMovCompleto290526Historico(CpTblMovCompleto290526Base):
    fecha_descarga = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = "cp_tbl_mov_completo_29_05_26_historico"

class CuadroVacancia(models.Model):
    fecha = models.DateField(unique=True)
    ocupadas_permanente = models.IntegerField(default=0)
    ocupadas_eventual = models.IntegerField(default=0)
    ocupadas_total = models.IntegerField(default=0)
    vacantes_permanente = models.IntegerField(default=0)
    vacantes_eventual = models.IntegerField(default=0)
    vacantes_total = models.IntegerField(default=0)
    total_permanente = models.IntegerField(default=0)
    total_eventual = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    class Meta:
        db_table = 'cuadro_vacancia'
        verbose_name = 'Cuadro Vacancia'
        verbose_name_plural = 'Cuadros Vacancia'

# Columnas personalizadas admitidas en tbl_columnas_plantilla_quincenal.
# Añadir aquí una nueva key es suficiente para habilitarla — no requiere migración.
#
# "fecha_genera_vacante" (columna AQ) NO está aquí: aunque el Excel la trae,
# el sistema debe priorizar SIEMPRE la fecha calculada (fecha_vacancia de
# MOV_POS, vía el SP de ZAFIRO sp_obtener_todas_vacancias) porque el Excel
# tiene errores conocidos en esta columna — se unificó con el valor que ya
# muestra Mov. Posiciones en su columna "Fecha de Vacancia", dejó de ser
# editable y ya no se carga del Excel (ver plantilla.views._get_fecha_vacancia_bulk_map).
COLUMNAS_QUINCENAL_VALIDAS = {
    "fecha_anuencia_detalle",                    # AL — texto libre (viene mixto en el Excel)
    "oficios_autorizacion_shcp",                 # AM
    "plazas_eventuales_autorizacion_2026",        # AN
    "candidato",                                 # AO
    "reportada",                                 # AP — Si / No (select en frontend)
    "cap_anual",                                 # AR
    "cap_mensual",                               # AS
    "observaciones_plantillas_do",               # AT
    "observaciones_proyectos_alineaciones",      # AU
    "anno_vacancia",                             # AV
    "solicitante",                               # unidad + oficio que solicita ocupar la vacante
    "nombre_candidato",                          # nombre del candidato propuesto
    "motivo_solicitud",                          # motivo de la solicitud (Promoción, Ingreso, etc.)
    "marca_no_disponible",                       # RFC='No Disponible' en el Excel (ej. plazas PASEM que no se pueden usar)
}

REPORTADA_CHOICES = ["Si", "No"]

# Subconjunto de COLUMNAS_QUINCENAL_VALIDAS que solo tiene sentido mientras la
# posición siga VACANTE — datos de un candidato solicitado (solicitante/
# nombre_candidato/motivo_solicitud) o la marca de "No Disponible" (RFC del
# Excel). Se blanquean en cada lectura si la posición ya está ocupada (ver
# EmpleadosCompletosActivosDetalleView y _aplicar_mapeos_detalle_excel; mismo
# criterio mov_pos_ocupadas_set que fecha_genera_vacante), para que nunca se
# muestre un dato "viejo" una vez que la plaza ya se llenó — sin que ningún
# job tenga que enterarse o limpiar nada en el momento de la lectura (aparte
# está el borrado PERMANENTE vía _limpiar_solicitudes_candidato_ocupadas en
# tasks.py, que corre cada 30 min dentro de importar_zafiro).
COLUMNAS_SOLICITUD_VACANTE = {"solicitante", "nombre_candidato", "motivo_solicitud", "marca_no_disponible"}

# "Fecha de Anuencia" (columna AL) no siempre es una fecha en el Excel: además
# de fechas reales y "-" (sin dato → cae al cálculo automático), existen estas
# 4 categorías de texto fijo (confirmadas contra datos reales). Un usuario que
# edite esta celda manualmente solo puede escribir una fecha 'YYYY-MM-DD' o
# una de estas categorías exactas — ver celda_override.registrar_override_fecha_anuencia.
FECHA_ANUENCIA_CATEGORIAS_VALIDAS = {"Nueva Creación", "En Proceso", "Sin Anuencia", "N/A"}


class TblColumnasPlantillaQuincenal(models.Model):
    """
    BASELINE de solo lectura de las columnas AL–AV del Excel de plantilla
    (``plantilla_con_columna_codigo.xlsx``), cargada por el management
    command ``cargar_columnas_quincenal`` — mismo espíritu que
    ``CatCorreccionPosicion``/``cargar_correcciones_plantilla`` (Código,
    Tipo de Aduana, DG de Aduana compactada), pero deliberadamente en una
    tabla separada porque estas SÍ son editables por el usuario (ver más
    abajo), a diferencia de las correcciones de solo lectura.

    IMPORTANTE: esta tabla NUNCA la escribe un usuario. Las ediciones
    manuales de estas columnas NO se guardan aquí — se registran en
    ``CeldaOverride`` (tabla=PLANTILLA_QUINCENAL, ver
    ``celda_override.registrar_y_aplicar_override_quincenal``), exactamente
    el mismo mecanismo de auditoría (valor_original/valor_nuevo/usuario/
    activo + historial) que ya existe para EMPLEADOS_COMPLETOS_SIG. La
    prioridad de lectura es: override activo del usuario > este baseline >
    "" (vacío) — así una edición manual sobrevive indefinidamente y una
    recarga del Excel (nuevo `cargar_columnas_quincenal`) solo actualiza el
    valor de referencia, nunca pisa lo que el usuario ya editó.

    Diseño clave-valor por posición: agregar una columna nueva en el futuro
    no requiere migración de BD, solo declarar la key en
    COLUMNAS_QUINCENAL_VALIDAS.

    Caso especial: ``fecha_anuencia_detalle`` (columna AL) no es editable a
    través de esta tabla/CeldaOverride(PLANTILLA_QUINCENAL) — se unificó con
    el sistema de "Fecha de Anuencia" ya existente para MOV_POS (ver
    ``celda_override._fecha_anuencia_default``), que ahora consulta este
    baseline como prioridad intermedia (Excel > cálculo automático), por
    encima de la cual el override manual de MOV_POS sigue mandando.
    """

    posicion = models.CharField(max_length=20, db_index=True)
    columna = models.CharField(max_length=100)          # key de COLUMNAS_QUINCENAL_VALIDAS
    valor = models.TextField(blank=True, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = "tbl_columnas_plantilla_quincenal"
        unique_together = [("posicion", "columna")]
        indexes = [
            models.Index(fields=["posicion"]),
        ]

    def __str__(self):
        return f"{self.posicion} · {self.columna} = {self.valor!r}"


class CeldaOverride(models.Model):
    """
    Edición manual de una celda sobre una tabla alimentada por ZAFIRO (que se
    trunca y recarga completa en cada `importar_zafiro`, ver tasks.py). No se
    escribe encima del import: se registra aquí y se reaplica sobre la tabla
    viva tanto al momento de editar como después de cada import (ver
    `plantilla.celda_override.aplicar_overrides_empleados_completos`).
    """

    tabla = models.CharField(max_length=64, choices=[
        ("EMPLEADOS_COMPLETOS_SIG", "Empleados"),
        ("BAJAS_SIG", "Bajas"),
        ("MOV_POS", "Movimientos Posición"),
        ("CP_TBL_HISTORIAL", "Histórico Movimientos"),
        ("PLANTILLA_QUINCENAL", "Columnas Quincenal (Plantilla Detalle)"),
        ("DATOS_PERSONALES", "Datos Personales"),
    ])
    clave_negocio = models.JSONField()
    clave_negocio_hash = models.CharField(max_length=64, db_index=True)
    columna = models.CharField(max_length=128)
    valor_original = models.TextField(null=True)
    valor_nuevo = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["tabla", "clave_negocio_hash", "columna", "activo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tabla", "clave_negocio_hash", "columna"],
                condition=models.Q(activo=True),
                name="uniq_override_activo",
            ),
        ]


class EmpleadoFotoAlias(models.Model):
    """
    Mapeo numempleado -> nombre real del archivo en media/empleados_fotos/,
    SOLO para fotos cuyo nombre no sigue la convención estándar
    ``<numempleado>.<ext>`` (ver FOTOS_EMPLEADOS_ANALISIS.md — la carga
    histórica trajo ~831 fotos nombradas por RFC en vez de número de
    empleado). El caso estándar se resuelve en vivo por convención de
    nombre, sin tocar esta tabla — así una foto nueva subida con el nombre
    correcto se ve de inmediato, sin depender de ningún proceso de
    sincronización. Esta tabla se llena una vez con el management command
    `cargar_fotos_empleados` y solo debería crecer si en el futuro alguien
    vuelve a subir una foto con un nombre no estándar (caso excepcional que
    se resolvería igual, a mano).
    """

    # OJO: EmpleadosCompletosSigBase.numempleado declara max_length=10, pero
    # los valores reales en BD tienen 11 caracteres (verificado: los 10,538
    # numempleado con RFC real miden 11) — ese max_length está desactualizado
    # respecto al dato real. Aquí se usa un margen mayor a propósito.
    numempleado = models.CharField(max_length=20, primary_key=True)
    nombre_archivo = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "EMPLEADO_FOTO_ALIAS"


class SuscripcionNotificacionPosicion(models.Model):
    """
    "Notificarme cuando la posición quede vacante/se ocupe" (menú contextual
    de la columna Posición en PlantillaDetalleTab/MovimientosTab). Se dispara
    en `notificaciones_posicion.procesar_suscripciones_posicion`, enganchado
    a la invalidación de caché tras cada `importar_zafiro` (ver tasks.py e
    `InvalidarCacheZafiroView` en views.py).

    `estado_conocido_al_suscribir` es un snapshot de "¿estaba ocupada?" al
    momento de crear la suscripción (no hay histórico de corridas de Celery
    para comparar contra el anterior) — la condición de disparo es que el
    estado ACTUAL difiera de este snapshot. Un solo aviso: al dispararse,
    `activa` pasa a False.

    `detalle_enviado` guarda el mismo contexto usado para renderizar el
    correo (ver `enviar_correo_vacancia`/`enviar_correo_ocupacion`) — se
    congela en ese momento porque MOV_POS/EMPLEADOS_COMPLETOS_SIG se
    truncan y recargan completas cada 30 min; sin este snapshot, el
    "campanita" de notificaciones (frontend) no podría mostrar qué decía
    el correo una vez que ZAFIRO vuelve a importar.
    """

    TIPO_CHOICES = [("VACANTE", "Vacante"), ("OCUPACION", "Ocupación")]
    ESTADO_CHOICES = [("O", "Ocupada"), ("V", "Vacante")]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="suscripciones_posicion",
    )
    posicion = models.CharField(max_length=20, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    activa = models.BooleanField(default=True, db_index=True)
    estado_conocido_al_suscribir = models.CharField(max_length=1, choices=ESTADO_CHOICES)
    creado_en = models.DateTimeField(auto_now_add=True)
    notificado_en = models.DateTimeField(null=True, blank=True)
    detalle_enviado = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    class Meta:
        db_table = "SUSCRIPCION_NOTIFICACION_POSICION"
        indexes = [
            models.Index(fields=["posicion", "activa"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "posicion", "tipo"],
                condition=models.Q(activa=True),
                name="uniq_suscripcion_activa_usuario_posicion_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.posicion} ({self.tipo})"


class FiltroGuardado(models.Model):
    """
    Combinación de condiciones de `AdvancedFiltersModal` guardada por un
    usuario para reaplicarla después sin reconstruirla a mano. `vista`
    identifica el tab de origen (cada uno tiene su propio set de columnas,
    p. ej. "plantilla_movimientos", "plantilla_bajas"), así que un filtro
    guardado en un tab no es intercambiable con otro. `condiciones` guarda
    tal cual la salida de `getValidAdvancedConditions` en el front (lista de
    `{column, condition, compareType, compareColumn, value, logic}`).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="filtros_guardados",
    )
    vista = models.CharField(max_length=50, db_index=True)
    nombre = models.CharField(max_length=100)
    condiciones = models.JSONField(encoder=DjangoJSONEncoder)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "FILTRO_GUARDADO"
        indexes = [
            models.Index(fields=["usuario", "vista"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "vista", "nombre"],
                name="uniq_filtro_guardado_usuario_vista_nombre",
            ),
        ]
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.usuario} - {self.vista} - {self.nombre}"


class AnuenciaAnexo(models.Model):
    """
    Historial de capturas del ANEXO 2 (Solicitud de Ocupación de Plazas y/o
    Contratación de Honorarios) — sub-tab "Anuencia" de Mov. Posiciones (ver
    AnuenciaTab.jsx). Cada registro es un anexo completo (un libro de Excel)
    que se puede recuperar para seguir editando o volver a generar su .xlsx.

    Tres eventos de auditoría distintos, cada uno con su propio usuario y
    fecha (no un solo "modificado_por" genérico, ver AuditedViewSetMixin en
    views.py): quién lo CREÓ (una sola vez), quién lo MODIFICÓ por última vez
    (cada guardado) y quién lo GENERÓ por última vez (cada descarga del
    .xlsx, con contador — un mismo anexo puede descargarse varias veces a lo
    largo de su vida, p. ej. si se corrige y se vuelve a mandar).

    ``on_delete=models.PROTECT`` en los 3: la baja de un usuario nunca debe
    borrar en cascada un registro de auditoría (mismo criterio que
    CeldaOverride.usuario).
    """

    # Un anexo es un LIBRO con N hojas (cada una se vuelve una pestaña del
    # .xlsx generado, ver construirWorkbookAnexo2 en anexo2Excel.js). Cada
    # hoja trae su propio cuadro de plazas, su Unidad Administrativa y su
    # justificación — una solicitud puede cubrir varias unidades, cada una
    # con su propia argumentación.
    #
    # Forma de cada elemento (la escribe el front tal cual, ver
    # `crearHojaVacia` en anexo2Schema.js):
    #     {
    #       "_id": "<uuid local, sólo para el key de React>",
    #       "nombre": "<nombre de la pestaña>",
    #       "unidad_administrativa": "...",
    #       "justificacion": "...",
    #       "filas": [ {<las 12 columnas del cuadro>}, ... ],
    #       "_unidades_detectadas": ["...", ...]
    #     }
    #
    # Es un JSONField y no un modelo hijo a propósito: las hojas no se
    # consultan, filtran ni referencian por separado — sólo se guardan y se
    # devuelven completas junto con su anexo.
    hojas = models.JSONField(default=list)
    firma_nombre = models.CharField(max_length=255, blank=True, default="Nombre y Firma de la DRH")
    firma_puesto = models.CharField(max_length=255, blank=True, default="Directora de Recursos Humanos")
    nombre_archivo = models.CharField(
        max_length=255, blank=True, default="Anexo 2 solicitud de ocupación de plazas"
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="anexos_anuencia_creados"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="anexos_anuencia_modificados",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="anexos_anuencia_generados",
    )
    generado_en = models.DateTimeField(null=True, blank=True)
    veces_generado = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-actualizado_en"]
        verbose_name = "Anexo de Anuencia"
        verbose_name_plural = "Anexos de Anuencia"

    def __str__(self):
        return f"Anexo {self.id} · {self.nombre_archivo or 'sin nombre'}"


class AnuenciaAnexo3Version(models.Model):
    """
    Una "versión" guardada del Anexo 3 (FUMP) generado a partir de un
    AnuenciaAnexo (Anexo 2). El Anexo 3 se arma agrupando las plazas del
    Anexo 2 por hoja + fecha de alta (ver AnuenciaAnexo3View), pero ese
    agrupamiento se puede corregir a mano arrastrando plazas entre hojas del
    resultado (ver Anexo3Editor.jsx) — como esa corrección es editable, un
    mismo Anexo 2 puede tener varios acomodos guardados a la vez, cada uno
    una versión distinta.

    Se guardan tanto los AJUSTES (`overrides`/`reasignaciones`, lo mínimo
    para poder recalcular contra los datos actuales al reabrir) como un
    `grupos` ya calculado (snapshot, sólo para listar/previsualizar sin
    tener que recomputar) — al reabrir una versión para seguir editando
    SIEMPRE se recalcula en el momento contra `overrides`/`reasignaciones`,
    nunca se confía ciegamente en el snapshot (el tabulador pudo cambiar
    desde que se guardó).
    """

    anexo = models.ForeignKey(AnuenciaAnexo, on_delete=models.CASCADE, related_name="anexo3_versiones")
    nombre = models.CharField(max_length=255)

    # {"<clave_de_grupo>": {"fecha_fin": "YYYY-MM-DD", "nombre_hoja": "..."}}
    overrides = models.JSONField(default=dict, blank=True)
    # {"<codigo_federal_de_puesto>": "<clave_de_grupo_destino>"}
    reasignaciones = models.JSONField(default=dict, blank=True)
    # Snapshot de la respuesta de AnuenciaAnexo3View al momento de guardar.
    grupos = models.JSONField(default=list, blank=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="anexo3_versiones_creadas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="anexo3_versiones_modificadas",
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado_en"]
        constraints = [
            models.UniqueConstraint(fields=["anexo", "nombre"], name="uniq_anexo3_version_nombre_por_anexo"),
        ]
        verbose_name = "Versión de Anexo 3"
        verbose_name_plural = "Versiones de Anexo 3"

    def __str__(self):
        return f"Anexo3 v.{self.id} · {self.nombre} (anexo {self.anexo_id})"


class AnuenciaJustificacionCatalogo(models.Model):
    """
    Catálogo de justificaciones reutilizables para la tabla de "Justificación"
    del Anexo 2 (sub-tab "Anuencia" de Mov. Posiciones, ver AnuenciaTab.jsx).

    Muchas solicitudes repiten argumentos casi idénticos (p. ej. "cubrir
    licencia médica", "carga de trabajo por incremento de operaciones"), así
    que el usuario guarda aquí las que usa seguido y las inserta en la hoja
    que esté editando con un clic (ver JustificacionCatalogoModal.jsx), en
    vez de reescribirlas cada vez.
    """

    nombre = models.CharField(max_length=255)
    texto = models.TextField()
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="justificaciones_anuencia_creadas"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Justificación de Anuencia (catálogo)"
        verbose_name_plural = "Justificaciones de Anuencia (catálogo)"


class SuscripcionApiControlPlazas(models.Model):
    """
    Consumidores externos de la API de Control de Plazas (ej.
    rendicionCuentasBack) que mantienen su propia caché sobre estos mismos
    datos y necesitan enterarse cuando cambian. Ver
    `cache_invalidation.invalidar_todo_el_cache_servidor`: al invalidar la
    caché local, se hace POST a `url` de cada suscriptor activo con
    `Authorization: Token <token>` para que también invalide la suya.

    `token` es un secreto compartido (no un Token de DRF de este proyecto):
    el consumidor lo valida a su manera contra el mismo valor.
    """

    nombre = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=500)
    token = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "SUSCRIPCION_API_CONTROL_PLAZAS"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
