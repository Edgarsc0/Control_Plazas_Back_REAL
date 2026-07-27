import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from plantilla.models import EmpleadoFotoAlias, EmpleadosCompletosSig

FOTOS_DIR = Path(settings.MEDIA_ROOT) / "empleados_fotos"
EXTENSIONES_FOTO = {".jpg", ".jpeg", ".png"}

# Un `numempleado` limpio se resuelve EN VIVO por convención de nombre
# (ver plantilla.views.EmpleadoFotoView) — este comando solo necesita
# registrar en EmpleadoFotoAlias las excepciones cuyo archivo real en disco
# NO se llama `<numempleado>.<ext>` (ver FOTOS_EMPLEADOS_ANALISIS.md):
#   - Nombradas por RFC (~831): se cruzan contra EmpleadosCompletosSig.rfc.
#   - Grupos con variantes SIN ninguna versión limpia (`<num>.ext`): quedan
#     fuera, requieren revisión manual (ver el .md).
#   - Nombres sin ningún patrón reconocible: quedan fuera, revisión manual.
RFC_RE = re.compile(r"^[A-Za-z]{4}\d{6}[A-Za-z0-9]{0,3}$")
NUMERICO_RE = re.compile(r"^\d+$")


class Command(BaseCommand):
    help = (
        "Carga inicial de EmpleadoFotoAlias: cruza contra EmpleadosCompletosSig.rfc "
        "las fotos de media/empleados_fotos/ cuyo nombre de archivo es un RFC en "
        "vez de un numempleado. Las fotos ya nombradas '<numempleado>.<ext>' NO "
        "necesitan pasar por aquí — se resuelven en vivo por convención de nombre. "
        "Ver FOTOS_EMPLEADOS_ANALISIS.md para el detalle completo del análisis."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Sin esta bandera solo se imprime el reporte (dry-run); con ella se escribe en BD.",
        )

    def handle(self, *args, **options):
        aplicar = options["aplicar"]

        if not FOTOS_DIR.exists():
            self.stderr.write(self.style.ERROR(f"No existe la carpeta {FOTOS_DIR}"))
            return

        archivos = sorted(p.name for p in FOTOS_DIR.iterdir() if p.is_file())
        self.stdout.write(f"Total de archivos en {FOTOS_DIR}: {len(archivos)}")

        # Lista (numempleado, rfc normalizado) para cruzar por PREFIJO: los
        # nombres de archivo históricos son el RFC SIN homoclave (10
        # caracteres: 4 letras + 6 dígitos), mientras que el RFC real en BD
        # sí trae la homoclave completa (13 caracteres) — un match exacto
        # nunca funcionaría (verificado: de 823 archivos con forma de RFC,
        # un match exacto solo resolvía 10; por prefijo resuelve la inmensa
        # mayoría). `rfc=' '` (un espacio) es el valor "sin RFC" real en esta
        # tabla, no ``''`` — hay que excluirlo explícitamente.
        reales = [
            (numempleado, rfc.strip().upper())
            for numempleado, rfc in EmpleadosCompletosSig.objects.exclude(
                rfc__isnull=True
            ).exclude(rfc="").exclude(rfc=" ").values_list("numempleado", "rfc")
            if rfc.strip()
        ]

        resueltos = {}  # numempleado -> nombre_archivo
        sin_match_rfc = []
        ambiguos_rfc = []
        omitidos_sin_patron = []
        omitidos_ya_limpios = 0

        for nombre in archivos:
            stem = Path(nombre).stem
            ext = Path(nombre).suffix.lower()

            if NUMERICO_RE.match(stem):
                # Ya sea limpio o parte de un grupo con variantes que sí tiene
                # una versión limpia: se resuelve en vivo, no necesita alias.
                # Los 2 grupos sin versión limpia (ver .md) tampoco se tocan
                # aquí — quedan para revisión manual, igual que los omitidos.
                omitidos_ya_limpios += 1
                continue

            if ext not in EXTENSIONES_FOTO:
                omitidos_sin_patron.append(nombre)
                continue

            stem_norm = stem.strip().upper()
            if not RFC_RE.match(stem_norm):
                omitidos_sin_patron.append(nombre)
                continue

            # Match por PREFIJO (ver comentario arriba de `reales`): el
            # archivo trae el RFC sin homoclave, la BD sí la tiene completa.
            coincidencias = [n for n, rfc in reales if rfc.startswith(stem_norm)]
            distintos = set(coincidencias)
            if not distintos:
                sin_match_rfc.append(nombre)
            elif len(distintos) > 1:
                ambiguos_rfc.append(f"{nombre} (coincide con {len(distintos)} empleados: {sorted(distintos)})")
            else:
                resueltos[coincidencias[0]] = nombre

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Resueltos por RFC (prefijo, sin homoclave): {len(resueltos)}"))
        self.stdout.write(f"Ya limpios (<numempleado>.ext, se resuelven en vivo, sin alias): {omitidos_ya_limpios}")
        self.stdout.write(f"Con forma de RFC pero SIN empleado correspondiente: {len(sin_match_rfc)}")
        self.stdout.write(f"Con forma de RFC pero AMBIGUO (varios empleados posibles): {len(ambiguos_rfc)}")
        self.stdout.write(f"Sin patrón reconocible (omitidos, ver FOTOS_EMPLEADOS_ANALISIS.md): {len(omitidos_sin_patron)}")

        if sin_match_rfc:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("RFC sin empleado correspondiente:"))
            for f in sin_match_rfc:
                self.stdout.write(f"  {f}")

        if ambiguos_rfc:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("RFC ambiguo (requiere revisión manual):"))
            for f in ambiguos_rfc:
                self.stdout.write(f"  {f}")

        if not aplicar:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Dry-run: no se escribió nada. Vuelve a correr con --aplicar para persistir."))
            return

        with transaction.atomic():
            EmpleadoFotoAlias.objects.all().delete()
            EmpleadoFotoAlias.objects.bulk_create(
                [
                    EmpleadoFotoAlias(numempleado=numempleado, nombre_archivo=nombre_archivo)
                    for numempleado, nombre_archivo in resueltos.items()
                ],
                batch_size=500,
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{len(resueltos)} alias guardados en EmpleadoFotoAlias."))
