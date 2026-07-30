"""
Management command: cargar_correcciones_plantilla
===================================================
Recarga completa el catálogo `cat_correccion_posicion` desde el Excel de
referencia — Código (columna AC), Tipo de Aduana (columna AE) y DG o Aduana
compactada (columna AK). Reemplaza al viejo comando `cargar_codigos`
(migrado a esta misma tabla, ver migración 0035).

Uso:
    python manage.py cargar_correcciones_plantilla
    python manage.py cargar_correcciones_plantilla --excel /ruta/alternativa/archivo.xlsx

Se apoya en la POSICIÓN de columna (A, AC, AE, AK), no en el texto del
encabezado.

Este catálogo es de SOLO LECTURA: corrige/completa columnas donde
EMPLEADOS_COMPLETOS_SIG (alimentada por ZAFIRO) trae un valor vacío o nunca
lo trae, para que la plantilla del sistema coincida con la del Excel —
- "Código": ZAFIRO nunca lo trae.
- "Tipo de Aduana"/"DG o Aduana compactada": ~33% de las posiciones vienen
  vacías en ZAFIRO pero el Excel siempre las trae (confirmado por
  validación cruzada Excel vs sistema).

NUNCA lo edita un usuario — a diferencia de `tbl_columnas_plantilla_quincenal`
(columnas AL–AV, editables y auditadas con CeldaOverride), esta tabla es
deliberadamente de solo lectura y separada de esa lógica. El comando hace un
refresh completo (borra y recarga) porque no hay auditoría que preservar.

Agregar una columna nueva en el futuro no requiere migración de BD: solo
declarar la key en COLUMNAS_CORRECCION_VALIDAS (plantilla/models.py) y
sumarla al mapeo de columnas de este comando.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

EXCEL_DEFAULT = Path(__file__).resolve().parents[3] / "plantilla_con_columna_codigo.xlsx"

# {columna en cat_correccion_posicion: índice 0-based en el Excel de referencia}
# A=0 (Posición), AC=28 (Código), AE=30 (Tipo de Aduana), AK=36 (DG o Aduana compactada).
COLUMNAS_EXCEL = {
    "codigo": 28,
    "tipo_de_aduana": 30,
    "dg_o_aduana_compactada": 36,
}


class Command(BaseCommand):
    help = "Recarga cat_correccion_posicion desde el Excel de referencia (Código, Tipo de Aduana, DG de Aduana compactada)."

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

        from plantilla.models import CatCorreccionPosicion

        excel_path = Path(options["excel"])
        if not excel_path.exists():
            raise CommandError(f"No se encontró el archivo Excel en: {excel_path}")

        self.stdout.write(f"Leyendo {excel_path} ...")

        columnas_ordenadas = sorted(COLUMNAS_EXCEL.values())
        try:
            # keep_default_na=False: 'N/A'/'NULL'/etc. literales no deben
            # convertirse en NaN (mismo bug ya corregido en cargar_columnas_quincenal).
            df = pd.read_excel(excel_path, header=0, usecols=[0, *columnas_ordenadas], keep_default_na=False)
        except Exception as exc:
            raise CommandError(f"Error al leer el Excel: {exc}")

        if df.shape[1] != len(columnas_ordenadas) + 1:
            raise CommandError(
                f"Se esperaban {len(columnas_ordenadas) + 1} columnas (Posición + "
                f"{list(COLUMNAS_EXCEL)}), se leyeron {df.shape[1]}. ¿Cambió la estructura del Excel?"
            )

        nombre_por_indice = {idx: nombre for nombre, idx in COLUMNAS_EXCEL.items()}
        df.columns = ["posicion", *[nombre_por_indice[idx] for idx in columnas_ordenadas]]
        df["posicion"] = df["posicion"].astype(str).str.strip()
        df = df[df["posicion"] != ""]

        self.stdout.write(f"  {len(df)} filas válidas encontradas en el Excel.")

        nuevas = []
        for _, fila in df.iterrows():
            posicion = fila["posicion"]
            for columna in COLUMNAS_EXCEL:
                valor_crudo = fila[columna]
                if valor_crudo is None or (isinstance(valor_crudo, float) and valor_crudo != valor_crudo):
                    continue
                valor = str(valor_crudo).strip()
                if not valor:
                    continue
                nuevas.append(CatCorreccionPosicion(posicion=posicion, columna=columna, valor=valor))

        with transaction.atomic():
            CatCorreccionPosicion.objects.all().delete()
            CatCorreccionPosicion.objects.bulk_create(nuevas, batch_size=1000)

        from django.core.cache import cache

        cache.delete_many([f"cat_correccion_posicion_mapa_{c}" for c in COLUMNAS_EXCEL])
        cache.delete_many(["empleados_completos_activos_detalle", "active_employees_filtered"])

        total_bd = CatCorreccionPosicion.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f"\nCatálogo listo: {total_bd} valores en cat_correccion_posicion.")
        )
