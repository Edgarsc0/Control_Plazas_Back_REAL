from django.core.management.base import BaseCommand

from plantilla.models import OrganigramaAnam
from plantilla.organigrama_tree import LEVEL_ORDER


class Command(BaseCommand):
    help = (
        "Reordena una sola vez el CSV `subordinados` existente (nivel desc, "
        "descripción) para que el orden visual no cambie al quitar el "
        "reordenamiento automático que build_tree_node aplicaba en cada "
        "request. NO recalcula relaciones padre-hijo (a diferencia de "
        "poblar_subordinados_organigrama, que sí las recalcula desde el "
        "determinante y borraría ediciones manuales — no volver a correr "
        "ese comando para esto)."
    )

    def handle(self, *args, **options):
        actualizados = 0
        rows = OrganigramaAnam.objects.exclude(subordinados__isnull=True).exclude(subordinados="")
        for row in rows:
            codes = [c for c in row.subordinados.split(",") if c]
            if len(codes) <= 1:
                continue

            hijos = {c.departamento: c for c in OrganigramaAnam.objects.filter(departamento__in=codes)}
            ordenados = sorted(
                codes,
                key=lambda c: (
                    -LEVEL_ORDER.get(hijos[c].nivel_direccion, 0) if c in hijos else 0,
                    hijos[c].descripcion_larga if c in hijos else "",
                ),
            )
            nuevo_valor = ",".join(ordenados)
            if nuevo_valor != row.subordinados:
                row.subordinados = nuevo_valor
                row.save(update_fields=["subordinados"])
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(f"{actualizados} departamentos reordenados."))
