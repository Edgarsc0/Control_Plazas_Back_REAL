from django.core.management.base import BaseCommand
from django.db import transaction

from plantilla.models import OrganigramaAnam
from plantilla.organigrama_tree import build_position_index, candidate_parents, find_root, resolve_by_position


class Command(BaseCommand):
    help = (
        "Repara nodos 'huérfanos' de Vista Institucional: filas de "
        "ORGANIGRAMA_ANAM que no son alcanzables desde la raíz caminando "
        "`subordinados` (normalmente porque quedaron sin enlazar tras "
        "crearse/editarse manualmente). Para cada huérfano 'raíz' (nadie lo "
        "referencia en ningún `subordinados`), resuelve su padre real con "
        "el mismo algoritmo de segmentación que usa Vista Alineación "
        "(candidate_parents/resolve_by_position) y, SOLO SI el padre "
        "resuelto ya es alcanzable, agrega el código al `subordinados` de "
        "ese padre. No modifica ningún enlace existente, solo agrega los "
        "que faltan. Los huérfanos 'encadenados' (ya enlazados a otro "
        "huérfano) se resuelven solos en cuanto se reconecta la raíz de su "
        "rama — no requieren cambio propio."
    )

    def handle(self, *args, **options):
        unidades = OrganigramaAnam.objects.values_list("unidad_negocio", flat=True).distinct()
        total_reparados = 0

        for unidad in unidades:
            rows = list(OrganigramaAnam.objects.filter(unidad_negocio=unidad).values(
                "departamento", "subordinados", "nivel_direccion", "descripcion_larga",
                "num_posicion_gerente", "posicion_director",
            ))
            if not rows:
                continue

            by_code = {r["departamento"]: r for r in rows}
            root = find_root(rows)

            visited = set()

            def walk(code):
                if code in visited or code not in by_code:
                    return
                visited.add(code)
                for c in (by_code[code]["subordinados"] or "").split(","):
                    if c:
                        walk(c)

            walk(root["departamento"])

            orphans = [r for r in rows if r["departamento"] not in visited]
            if not orphans:
                continue

            referenced_by = set()
            for r in rows:
                for c in (r["subordinados"] or "").split(","):
                    if c:
                        referenced_by.add(c)
            top_orphans = [r for r in orphans if r["departamento"] not in referenced_by]

            if not top_orphans:
                self.stdout.write(self.style.WARNING(
                    f"{unidad}: {len(orphans)} huérfano(s) pero ninguno es 'raíz' de su rama "
                    f"(posible referencia circular entre ellos) — se omite, requiere revisión manual."
                ))
                continue

            available = {r["departamento"] for r in rows}
            by_mgr = build_position_index(rows)

            reparados_unidad = 0
            for r in top_orphans:
                code = r["departamento"]
                cands = candidate_parents(code, available)
                resuelto = cands[0] if cands else resolve_by_position(r, by_mgr, available)
                if not resuelto or resuelto not in visited:
                    self.stdout.write(self.style.WARNING(
                        f"  {unidad}: {code} no se pudo resolver de forma segura "
                        f"(padre resuelto={resuelto!r}), se omite — requiere revisión manual."
                    ))
                    continue

                with transaction.atomic():
                    padre = OrganigramaAnam.objects.select_for_update().get(departamento=resuelto)
                    existentes = [c for c in (padre.subordinados or "").split(",") if c]
                    if code not in existentes:
                        existentes.append(code)
                        padre.subordinados = ",".join(existentes)
                        padre.save(update_fields=["subordinados"])
                        reparados_unidad += 1

            if reparados_unidad:
                self.stdout.write(self.style.SUCCESS(
                    f"{unidad}: {reparados_unidad} nodo(s) raíz reconectado(s) "
                    f"(de {len(orphans)} huérfanos totales en esa unidad)."
                ))
            total_reparados += reparados_unidad

        self.stdout.write(self.style.SUCCESS(f"Total reconectados: {total_reparados}"))
