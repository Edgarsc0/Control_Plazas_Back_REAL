from django.core.management.base import BaseCommand
from django.db import transaction

from plantilla.models import OrganigramaAnam, OrganigramaAnamSig


class Command(BaseCommand):
    help = (
        "Congela una foto fija de las filas ORGANIGRAMA_ANAM con "
        "isSIGInfo=1 en la tabla ORGANIGRAMA_ANAM_SIG, exclusiva de Vista "
        "SIG. Trunca y vuelve a poblar por completo la tabla destino (no "
        "un merge) — correr de nuevo solo si se decide 'resetear' la foto "
        "oficial a lo que hoy dice ORGANIGRAMA_ANAM.isSIGInfo=1."
    )

    def handle(self, *args, **options):
        origen = OrganigramaAnam.objects.filter(isSIGInfo=True).values(
            "departamento", "descripcion_larga", "nivel_direccion", "unidad_negocio",
            "unidad_administrativa", "doaf", "num_posicion_gerente", "posicion_director",
        )
        objetos = [OrganigramaAnamSig(**row) for row in origen]

        with transaction.atomic():
            OrganigramaAnamSig.objects.all().delete()
            OrganigramaAnamSig.objects.bulk_create(objetos, batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"{len(objetos)} filas congeladas en ORGANIGRAMA_ANAM_SIG."))
