"""
Management command: cargar_codigos
===================================
Pobla (o actualiza) la tabla `cat_codigo_posicion` a partir del archivo Excel
de referencia que contiene la columna 'Código' (col AC) por posición (col A).

Uso:
    python manage.py cargar_codigos
    python manage.py cargar_codigos --excel /ruta/alternativa/archivo.xlsx

El comando es IDEMPOTENTE: se puede ejecutar múltiples veces sin efectos
secundarios (inserta nuevos, actualiza los que cambiaron, ignora los que no
cambiaron). Una vez poblado el catálogo, el archivo Excel puede archivarse o
eliminarse — el dato persiste en la BD y el código no cambia por sincronización
automática de Celery.
"""

import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Ruta por defecto del Excel: mismo directorio que manage.py (raíz del proyecto Django)
# Estructura: commands/ → management/ → plantilla/ → Control_Plazas_Back_REAL/
EXCEL_DEFAULT = Path(__file__).resolve().parents[3] / "plantilla_con_columna_codigo.xlsx"


class Command(BaseCommand):
    help = "Pobla cat_codigo_posicion desde el Excel de referencia (col A=Posición, col AC=Código)."

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

        from plantilla.models import CatCodigoPosicion

        excel_path = Path(options["excel"])
        if not excel_path.exists():
            raise CommandError(f"No se encontró el archivo Excel en: {excel_path}")

        self.stdout.write(f"Leyendo {excel_path} ...")

        try:
            df = pd.read_excel(excel_path, usecols=["Posición", "Código"], dtype=str)
        except Exception as exc:
            raise CommandError(f"Error al leer el Excel: {exc}")

        # Limpiar y filtrar filas válidas
        df["Posición"] = df["Posición"].str.strip()
        df["Código"] = df["Código"].str.strip()
        df = df.dropna(subset=["Posición"])
        df = df[df["Posición"] != ""]

        total_excel = len(df)
        self.stdout.write(f"  {total_excel} filas válidas encontradas en el Excel.")

        # Construir diccionario posición → código desde el Excel
        mapa_excel = dict(zip(df["Posición"], df["Código"]))

        # Traer catálogo existente en BD
        existentes = dict(CatCodigoPosicion.objects.values_list("plaza", "codigo"))

        nuevas = []
        por_actualizar = []

        for plaza, codigo in mapa_excel.items():
            if plaza not in existentes:
                nuevas.append(CatCodigoPosicion(plaza=plaza, codigo=codigo))
            elif existentes[plaza] != codigo:
                por_actualizar.append(CatCodigoPosicion(plaza=plaza, codigo=codigo))
            # Si ya existe y es igual, no se hace nada

        # Insertar nuevas
        if nuevas:
            CatCodigoPosicion.objects.bulk_create(nuevas, batch_size=1000, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"  ✓ {len(nuevas)} posiciones nuevas insertadas."))
        else:
            self.stdout.write("  Sin posiciones nuevas que insertar.")

        # Actualizar existentes con código distinto
        if por_actualizar:
            CatCodigoPosicion.objects.bulk_update(por_actualizar, ["codigo"], batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f"  ✓ {len(por_actualizar)} códigos actualizados."))
        else:
            self.stdout.write("  Sin códigos que actualizar.")

        total_bd = CatCodigoPosicion.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCatálogo listo: {total_bd} registros en cat_codigo_posicion."
            )
        )
        self.stdout.write(
            "Puedes archivar o eliminar el archivo Excel — el dato ya está en la BD."
        )
