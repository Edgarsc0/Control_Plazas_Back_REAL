"""Crea los roles titulares de unidad: uno por Unidad de Negocio (13) y, bajo
los de DGOA y UAF, uno por cada Unidad Administrativa adscrita (50 aduanas +
2 direcciones operativas) — 65 en total. Ver RolPerfil.

Idempotente: identifica cada rol por su unidad (RolPerfil.cd_un/cd_ua), nunca
por nombre, y solo CREA lo que falta. Un rol que ya existe no se toca — sus
permisos pudieron personalizarse a mano después de crearlo.

    python manage.py crear_roles_unidades --dry-run
    python manage.py crear_roles_unidades
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authentication.models import RolColumnScope, RolPerfil, RolUaScope, RolUnScope
from authentication.ua_catalog import UA_CATALOG, uas_adscritas
from authentication.un_catalog import UN_CATALOG


class Command(BaseCommand):
    help = "Crea los 65 roles titulares (13 UN + 52 UA adscritas) a partir de un rol plantilla."

    def add_arguments(self, parser):
        parser.add_argument(
            "--plantilla",
            default="DGPEDA",
            help="Rol del que se copian permisos y columnas visibles (default: DGPEDA).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Muestra qué crearía, sin escribir.")

    def handle(self, *args, **opts):
        try:
            plantilla = Group.objects.get(name=opts["plantilla"])
        except Group.DoesNotExist:
            raise CommandError(f'No existe el rol plantilla "{opts["plantilla"]}".')

        # Los titulares son de solo consulta: se copian los permisos de la
        # plantilla SIN los de edición (ninguna vista de escritura recorta por
        # unidad, así que a un rol con alcance se le niegan de todos modos).
        permisos = [p for p in plantilla.permissions.all() if not p.codename.startswith("edit_")]
        columnas_cfg = RolColumnScope.objects.filter(rol=plantilla).first()
        columnas = list(columnas_cfg.columnas_permitidas) if columnas_cfg else None

        self.stdout.write(
            f'Plantilla "{plantilla.name}": {len(permisos)} permisos de consulta '
            f'({", ".join(sorted(p.codename for p in permisos))}); '
            f'columnas: {"sin restricción" if columnas is None else len(columnas)}'
        )

        creados = 0
        existentes = 0
        with transaction.atomic():
            for cd_un, nombre_un in UN_CATALOG.items():
                titular_un, creado = self._titular(
                    nombre_un, cd_un, "", None, permisos, columnas
                )
                creados += creado
                existentes += not creado
                for cd_ua in uas_adscritas(cd_un):
                    _, creado = self._titular(
                        UA_CATALOG[cd_ua][1], cd_un, cd_ua, titular_un, permisos, columnas
                    )
                    creados += creado
                    existentes += not creado
            if opts["dry_run"]:
                transaction.set_rollback(True)

        verbo = "Se crearían" if opts["dry_run"] else "Creados"
        self.stdout.write(self.style.SUCCESS(f"{verbo}: {creados}. Ya existían: {existentes}."))

    def _titular(self, nombre, cd_un, cd_ua, padre, permisos, columnas):
        perfil = RolPerfil.objects.filter(cd_un=cd_un, cd_ua=cd_ua).select_related("rol").first()
        if perfil:
            return perfil.rol, False

        if Group.objects.filter(name=nombre).exists():
            raise CommandError(
                f'Ya existe un rol llamado "{nombre}" que no es el titular de la unidad '
                f"{cd_un}/{cd_ua or '-'}. Renómbralo o elimínalo antes de continuar."
            )

        self.stdout.write(f"  + {'    ' if padre else ''}{nombre}  [UN {cd_un}{' · UA ' + cd_ua if cd_ua else ''}]")

        rol = Group.objects.create(name=nombre)
        rol.permissions.set(permisos)
        RolPerfil.objects.create(
            rol=rol,
            padre=padre,
            tipo=RolPerfil.TITULAR,
            cd_un=cd_un,
            cd_ua=cd_ua,
            max_usuarios=1,
            es_sistema=True,
        )
        # El alcance se guarda completo en cada titular (UN, y UA si aplica)
        # aunque el de UN también se heredaría del padre: así cada rol se
        # explica solo al verlo en la pantalla de roles.
        RolUnScope.objects.create(rol=rol, cd_un_codes=[cd_un])
        if cd_ua:
            RolUaScope.objects.create(rol=rol, cd_ua_codes=[cd_ua])
        # Las columnas visibles solo se guardan en los titulares raíz (UN): los
        # de UA adscrita las HEREDAN en vivo del padre, así un cambio en las
        # columnas de la UN les llega sin tener que editar 50 aduanas.
        if columnas is not None and padre is None:
            RolColumnScope.objects.create(rol=rol, columnas_permitidas=columnas)
        return rol, True
