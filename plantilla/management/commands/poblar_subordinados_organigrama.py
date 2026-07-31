from django.core.management.base import BaseCommand

from plantilla.models import OrganigramaAnam
from plantilla.organigrama_tree import build_parent_map, build_children_map


class Command(BaseCommand):
    help = (
        "Calcula la columna subordinados (hijos directos por código de "
        "departamento) de ORGANIGRAMA_ANAM, corriendo la misma lógica de "
        "segmentación de determinante que organigrama_tree.build_tree, "
        "por cada unidad_negocio. El cálculo de padres usa TODAS las filas "
        "de la unidad (hace falta el conjunto completo para resolver "
        "correctamente el determinante), pero el resultado solo se "
        "PERSISTE en las filas con isSIGInfo=1 (las que administra el "
        "pipeline automático) — las filas curadas a mano en Vista "
        "Institucional (isSIGInfo=0/NULL, nunca tocadas por el pipeline) "
        "quedan protegidas y conservan su subordinados manual/reordenado."
    )

    def handle(self, *args, **options):
        unidades = (
            OrganigramaAnam.objects.values_list("unidad_negocio", flat=True)
            .distinct()
        )

        total_updated = 0
        for unidad_negocio in unidades:
            rows = list(
                OrganigramaAnam.objects.filter(unidad_negocio=unidad_negocio).values(
                    "departamento",
                    "descripcion_larga",
                    "nivel_direccion",
                    "unidad_negocio",
                    "unidad_administrativa",
                    "doaf",
                    "num_posicion_gerente",
                    "posicion_director",
                    "isSIGInfo",
                )
            )
            if not rows:
                continue

            parent_map, _root_code = build_parent_map(rows)
            by_parent = build_children_map(rows, parent_map)

            objs = []
            for row in rows:
                if not row["isSIGInfo"]:
                    continue
                code = row["departamento"]
                children = by_parent.get(code, [])
                subordinados = ",".join(c["departamento"] for c in children)
                objs.append(OrganigramaAnam(departamento=code, subordinados=subordinados or None))

            if not objs:
                continue

            OrganigramaAnam.objects.bulk_update(objs, ["subordinados"], batch_size=500)
            total_updated += len(objs)
            self.stdout.write(
                f"unidad_negocio={unidad_negocio}: {len(objs)} departamentos actualizados (isSIGInfo=1)"
            )

        self.stdout.write(self.style.SUCCESS(f"Total actualizado: {total_updated}"))
