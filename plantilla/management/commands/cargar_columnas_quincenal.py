"""
Management command: cargar_columnas_quincenal
==============================================
Pobla (recarga completa) el BASELINE de referencia de
`tbl_columnas_plantilla_quincenal` a partir del archivo Excel de referencia
— mismo archivo y mismo patrón que `cargar_correcciones_plantilla`, pero
para las 10 columnas editables AL–AV (Fecha de Anuencia, Oficios de
Autorización SHCP, Plazas eventuales..., Candidato, Reportada, CAP ANUAL,
CAP MENSUAL, Observaciones - Plantillas DO, Observaciones - Proyectos y
Alineaciones, Año de Vacancia) MÁS las 3 columnas de solicitud de candidato
(Solicitante, Nombre del candidato, Motivo de solicitud — ver
COLUMNAS_SOLICITUD_EXCEL más abajo).

Uso:
    python manage.py cargar_columnas_quincenal
    python manage.py cargar_columnas_quincenal --excel /ruta/alternativa/archivo.xlsx

Se apoya en la POSICIÓN de columna (A, AL..AV), no en el texto del
encabezado: algunos encabezados del Excel traen saltos de línea (p.ej.
"CAP\\nANUAL"), frágiles de matchear por texto exacto.

IMPORTANTE — esta tabla es solo un BASELINE de referencia, nunca pisa
ediciones manuales de un usuario: esas viven aparte en CeldaOverride
(tabla=PLANTILLA_QUINCENAL, ver `plantilla.celda_override`). El comando hace
un refresh completo (borra y recarga) porque no hay auditoría que preservar
aquí — la auditoría real de lo que el usuario edita está en CeldaOverride, no
en esta tabla. Volver a correr este comando tras actualizar el Excel solo
actualiza el valor de referencia; si una posición ya tiene un override
activo, la lectura sigue mostrando ESE valor (el override gana, ver
`plantilla.views._get_mapa_quincenal` / `celda_override._fecha_anuencia_default`).

Caso especial 'fecha_anuencia_detalle' (columna AL): la mayoría de filas
traen solo '-' o vacío en el Excel — esas filas NO se cargan (así el sistema
de Fecha de Anuencia cae a su cálculo automático de fecha_vacancia + 30 días).
Solo se carga cuando el Excel trae una fecha real parseable.

NO se carga "Fecha que se genera la vacante" (columna AQ, índice 42): el
Excel tiene errores conocidos en esa columna — el sistema debe priorizar
SIEMPRE la fecha calculada (`fecha_vacancia` de MOV_POS, vía el SP de ZAFIRO),
unificada con la misma columna que ya muestra Mov. Posiciones — ver
`plantilla.views._get_fecha_vacancia_bulk_map`. Deliberadamente ausente de
COLUMNAS_EXCEL, no solo sin cargar.

Columnas de solicitud (Solicitante/Nombre del candidato/Motivo de solicitud):
en el Excel, cuando alguien solicita ocupar una plaza vacante, el capturista
escribe esos datos SOBRE las columnas RFC/CURP/Nombres/Motivo. CURP/Nombres/
Motivo se cargan tal cual (ver COLUMNAS_SOLICITUD_EXCEL); RFC no aporta un
dato de candidato en sí (solo trae el literal "Solicitada"/"No Disponible"),
pero SÍ distingue entre una solicitud real y una plaza marcada "No
Disponible" (ej. PASEM que no se puede usar) — ver marca_no_disponible más
abajo. Estas 4 columnas solo se cargan para filas con Estado Nómina
"Vacante"; en una posición ocupada, esas mismas columnas del Excel traen
datos REALES del empleado, no de un candidato solicitado, así que cargarlas
ahí sería incorrecto — ver ESTADO_NOMINA_EXCEL_IDX.
"""

import re
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

EXCEL_DEFAULT = Path(__file__).resolve().parents[3] / "plantilla_con_columna_codigo.xlsx"

# {columna en tbl_columnas_plantilla_quincenal: índice 0-based en el Excel de
# referencia}. AL=37 .. AV=47, salteando AQ=42 (ver docstring del módulo).
COLUMNAS_EXCEL = {
    "fecha_anuencia_detalle": 37,
    "oficios_autorizacion_shcp": 38,
    "plazas_eventuales_autorizacion_2026": 39,
    "candidato": 40,
    "reportada": 41,
    "cap_anual": 43,
    "cap_mensual": 44,
    "observaciones_plantillas_do": 45,
    "observaciones_proyectos_alineaciones": 46,
    "anno_vacancia": 47,
}

# Columnas de solicitud de candidato (ver docstring del módulo) — se leen de
# CURP/Nombres/Motivo y solo se cargan cuando Estado Nómina (índice 1) viene
# "Vacante" en esa fila. RFC (índice 3) NO aporta dato de candidato (solo
# trae el literal "Solicitada"/"No Disponible", redundante con CURP/Nombres
# para saber SI hay solicitud), pero SÍ distingue "No Disponible" (plazas
# PASEM que no se pueden usar) de una solicitud real — ver marca_no_disponible.
ESTADO_NOMINA_EXCEL_IDX = 1
RFC_EXCEL_IDX = 3
COLUMNAS_SOLICITUD_EXCEL = {
    "solicitante": 4,        # CURP: unidad + oficio que solicita la plaza
    "nombre_candidato": 5,   # Nombres: nombre del candidato propuesto
    "motivo_solicitud": 6,   # Motivo: motivo de la solicitud
}

_FECHA_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_fecha_anuencia(valor):
    """Normaliza el valor crudo de la columna AL: ``None`` si no trae dato
    (vacío o '-' — en ese caso el sistema cae al cálculo automático de
    fecha_vacancia + 30 días); 'YYYY-MM-DD' si es una fecha real; o el texto
    tal cual si es cualquier otra cosa (p.ej. una de las 4 categorías fijas
    "Nueva Creación"/"En Proceso"/"Sin Anuencia"/"N/A", u otro texto futuro) —
    se respeta el contenido del Excel en vez de descartarlo, ver
    FECHA_ANUENCIA_CATEGORIAS_VALIDAS en plantilla.models."""
    if valor is None:
        return None
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    texto = str(valor).strip()
    if not texto or texto == "-":
        return None
    if _FECHA_ISO_RE.match(texto):
        return texto
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(texto, fmt).date().isoformat()
        except ValueError:
            continue
    return texto


class Command(BaseCommand):
    help = "Recarga el baseline de tbl_columnas_plantilla_quincenal desde el Excel de referencia (columnas AL-AV)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--excel",
            type=str,
            default=str(EXCEL_DEFAULT),
            help="Ruta al archivo Excel. Por defecto: plantilla_con_columna_codigo.xlsx en la raíz del proyecto.",
        )

    def handle(self, *args, **options):
        try:
            import pandas as pd
        except ImportError:
            raise CommandError("pandas no está instalado. Ejecuta: pip install pandas openpyxl")

        from plantilla.models import TblColumnasPlantillaQuincenal

        excel_path = Path(options["excel"])
        if not excel_path.exists():
            raise CommandError(f"No se encontró el archivo Excel en: {excel_path}")

        self.stdout.write(f"Leyendo {excel_path} ...")

        columnas_ordenadas = sorted(COLUMNAS_EXCEL.values())
        extra_idx = sorted({ESTADO_NOMINA_EXCEL_IDX, RFC_EXCEL_IDX, *COLUMNAS_SOLICITUD_EXCEL.values()})
        todas_idx = sorted({0, *extra_idx, *columnas_ordenadas})
        try:
            # col 0 = Posición (A), el resto por posición (no por nombre de
            # encabezado, ver docstring del módulo).
            # keep_default_na=False: pandas por default trata como NaN varios
            # textos literales (p.ej. 'N/A', 'NA', 'NULL', 'None') — la
            # columna "Plazas eventuales..." SÍ trae 'N/A' como valor real y
            # con el default se perdía silenciosamente (confirmado: la celda
            # cruda vale 'N/A' vía openpyxl, pero pandas la leía como NaN).
            df = pd.read_excel(excel_path, header=0, usecols=todas_idx, keep_default_na=False)
        except Exception as exc:
            raise CommandError(f"Error al leer el Excel: {exc}")

        if df.shape[1] != len(todas_idx):
            raise CommandError(
                f"Se esperaban {len(todas_idx)} columnas, se leyeron {df.shape[1]}. "
                f"¿Cambió la estructura del Excel?"
            )

        nombre_por_indice = {0: "posicion", ESTADO_NOMINA_EXCEL_IDX: "estado_nomina_raw", RFC_EXCEL_IDX: "rfc_raw"}
        nombre_por_indice.update({idx: nombre for nombre, idx in COLUMNAS_EXCEL.items()})
        nombre_por_indice.update({idx: nombre for nombre, idx in COLUMNAS_SOLICITUD_EXCEL.items()})
        df.columns = [nombre_por_indice[idx] for idx in todas_idx]
        df["posicion"] = df["posicion"].astype(str).str.strip()
        df = df[df["posicion"] != ""]

        self.stdout.write(f"  {len(df)} filas válidas encontradas en el Excel.")

        nuevas = []
        for _, fila in df.iterrows():
            posicion = fila["posicion"]
            for columna in COLUMNAS_EXCEL:
                valor_crudo = fila[columna]

                if columna == "fecha_anuencia_detalle":
                    valor = _parse_fecha_anuencia(valor_crudo)
                    if valor is None:
                        continue
                else:
                    # `keep_default_na=False` ya evita que 'N/A'/'NULL'/etc.
                    # literales se conviertan en NaN, pero una celda con error
                    # de fórmula (#REF!, #DIV/0!) sí puede llegar como float
                    # NaN real — se descarta ese caso puntual aquí.
                    if valor_crudo is None or (isinstance(valor_crudo, float) and valor_crudo != valor_crudo):
                        continue
                    valor = str(valor_crudo).strip()
                    if not valor:
                        continue
                    if columna == "reportada" and valor not in ("Si", "No"):
                        continue

                nuevas.append(TblColumnasPlantillaQuincenal(posicion=posicion, columna=columna, valor=valor))

            # Solicitud de candidato: solo si la fila viene vacante en el
            # Excel (ver docstring del módulo) — en una posición ocupada,
            # CURP/Nombres/Motivo son datos reales del empleado, no de un
            # candidato solicitado. OJO: a diferencia de EMPLEADOS_COMPLETOS_SIG
            # (donde estado_nomina es un código A/S/L/P o vacío), en el Excel
            # "Estado Nómina" es el texto completo ("Vacante", "Activo", ...).
            if str(fila["estado_nomina_raw"]).strip() == "Vacante":
                for columna in COLUMNAS_SOLICITUD_EXCEL:
                    valor_crudo = fila[columna]
                    if valor_crudo is None or (isinstance(valor_crudo, float) and valor_crudo != valor_crudo):
                        continue
                    valor = str(valor_crudo).strip()
                    if not valor:
                        continue
                    nuevas.append(TblColumnasPlantillaQuincenal(posicion=posicion, columna=columna, valor=valor))

                # "No Disponible" (ej. plazas PASEM que no se pueden usar):
                # marca distinta de una solicitud real, aunque ambas comparten
                # el mismo Estado Nómina="Vacante" — ver COLUMNAS_SOLICITUD_EXCEL.
                if str(fila["rfc_raw"]).strip().upper() == "NO DISPONIBLE":
                    nuevas.append(TblColumnasPlantillaQuincenal(
                        posicion=posicion, columna="marca_no_disponible", valor="No Disponible",
                    ))

        with transaction.atomic():
            TblColumnasPlantillaQuincenal.objects.all().delete()
            TblColumnasPlantillaQuincenal.objects.bulk_create(nuevas, batch_size=1000)

        from django.core.cache import cache

        cache.delete_many([
            "tbl_columnas_quincenal_mapa",
            "empleados_completos_activos_detalle",
            "active_employees_filtered",
        ])

        total_bd = TblColumnasPlantillaQuincenal.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"\nBaseline listo: {total_bd} valores en tbl_columnas_plantilla_quincenal.")
        )
        self.stdout.write(
            "Las ediciones manuales de usuarios (CeldaOverride/PLANTILLA_QUINCENAL) no se tocaron."
        )
