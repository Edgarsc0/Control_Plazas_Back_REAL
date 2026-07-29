"""
Management command: cargar_columnas_quincenal
==============================================
Pobla (recarga completa) el BASELINE de referencia de
`tbl_columnas_plantilla_quincenal` a partir del archivo Excel de referencia
— mismo archivo y mismo patrón que `cargar_codigos` (columna 'Código', col
AC), pero para las 11 columnas editables AL–AV (Fecha de Anuencia, Oficios
de Autorización SHCP, Plazas eventuales..., Candidato, Reportada, Fecha que
se genera la vacante, CAP ANUAL, CAP MENSUAL, Observaciones - Plantillas DO,
Observaciones - Proyectos y Alineaciones, Año de Vacancia).

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
"""

import re
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

EXCEL_DEFAULT = Path(__file__).resolve().parents[3] / "plantilla_con_columna_codigo.xlsx"

# Orden fijo de columnas AL(0-based 37) .. AV(0-based 47) del Excel de referencia.
COLUMNAS_EXCEL_AL_AV = [
    "fecha_anuencia_detalle",
    "oficios_autorizacion_shcp",
    "plazas_eventuales_autorizacion_2026",
    "candidato",
    "reportada",
    "fecha_genera_vacante",
    "cap_anual",
    "cap_mensual",
    "observaciones_plantillas_do",
    "observaciones_proyectos_alineaciones",
    "anno_vacancia",
]

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

        try:
            # col 0 = Posición (A), cols 37..47 (0-based) = AL..AV — por
            # posición, no por nombre de encabezado (ver docstring del módulo).
            # keep_default_na=False: pandas por default trata como NaN varios
            # textos literales (p.ej. 'N/A', 'NA', 'NULL', 'None') — la
            # columna "Plazas eventuales..." SÍ trae 'N/A' como valor real y
            # con el default se perdía silenciosamente (confirmado: la celda
            # cruda vale 'N/A' vía openpyxl, pero pandas la leía como NaN).
            df = pd.read_excel(excel_path, header=0, usecols=[0, *range(37, 48)], keep_default_na=False)
        except Exception as exc:
            raise CommandError(f"Error al leer el Excel: {exc}")

        if df.shape[1] != 12:
            raise CommandError(
                f"Se esperaban 12 columnas (Posición + AL..AV), se leyeron {df.shape[1]}. "
                "¿Cambió la estructura del Excel?"
            )

        df.columns = ["posicion", *COLUMNAS_EXCEL_AL_AV]
        df["posicion"] = df["posicion"].astype(str).str.strip()
        df = df[df["posicion"] != ""]

        self.stdout.write(f"  {len(df)} filas válidas encontradas en el Excel.")

        nuevas = []
        for _, fila in df.iterrows():
            posicion = fila["posicion"]
            for columna in COLUMNAS_EXCEL_AL_AV:
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
