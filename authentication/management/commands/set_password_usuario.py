"""
Asigna la contraseña de un usuario de la whitelist desde la línea de comandos.

Existe para resolver el arranque en frío: las contraseñas se administran desde
Roles > Usuarios, pero para entrar a esa pantalla hay que estar logueado, y al
migrar del login por código de verificación nadie tenía contraseña todavía.
Con esto se le pone la primera al administrador; de ahí en adelante todo el
alta y restablecimiento se hace desde la UI.

    python manage.py set_password_usuario correo@anam.gob.mx
    python manage.py set_password_usuario correo@anam.gob.mx --password 'xxx'
"""
from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token

from authentication.models import Whitelist, sincronizar_usuario_django


class Command(BaseCommand):
    help = "Asigna la contraseña de un correo ya presente en la whitelist."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Correo de la entrada de whitelist.")
        parser.add_argument(
            "--password",
            help="Contraseña a asignar. Si se omite, se pide de forma interactiva "
            "(preferible: no queda en el historial del shell).",
        )
        parser.add_argument(
            "--no-forzar-cambio",
            action="store_true",
            help="No exigir al usuario que la cambie al entrar. Úsalo solo para "
            "tu propia cuenta, cuando nadie más conoce la contraseña.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()

        entry = Whitelist.objects.filter(email__iexact=email).select_related("rol").first()
        if entry is None:
            raise CommandError(
                f"'{email}' no está en la whitelist. Agrégalo primero desde "
                f"Roles > Usuarios o desde el admin de Django."
            )

        password = options["password"]
        if not password:
            password = getpass("Contraseña nueva: ")
            if password != getpass("Confírmala: "):
                raise CommandError("Las contraseñas no coinciden.")

        if not password:
            raise CommandError("La contraseña no puede estar vacía.")

        user = sincronizar_usuario_django(entry)

        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("\n".join(exc.messages))

        user.set_password(password)
        user.save(update_fields=["password"])

        entry.debe_cambiar_password = not options["no_forzar_cambio"]
        entry.save(update_fields=["debe_cambiar_password"])

        # Mismo criterio que el restablecimiento desde la UI: cortar sesiones
        # que siguieran vivas con la contraseña anterior.
        Token.objects.filter(user=user).delete()

        aviso = (
            " Deberá cambiarla al iniciar sesión."
            if entry.debe_cambiar_password
            else ""
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Contraseña actualizada para {entry.email} (rol: {entry.rol.name}).{aviso}"
            )
        )
