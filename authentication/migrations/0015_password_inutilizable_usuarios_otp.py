"""
Marca como inutilizables las contraseñas vacías que dejó el login por código.

El flujo anterior (OTP) creaba el ``User`` con ``get_or_create`` sin pasar
contraseña, lo que deja la columna en cadena vacía. Django considera USABLE
cualquier hash que no empiece con "!" — cadena vacía incluida — así que esos
usuarios se reportaban como "ya tienen contraseña" en Roles > Usuarios cuando
en realidad no pueden autenticarse por ningún medio (``check_password("")``
nunca identifica un hasher válido).

Reemplazarlas por un hash inutilizable deja consistente lo que muestra la UI
con lo que el sistema realmente permite, y hace evidente a qué usuarios les
falta que un administrador les asigne su primera contraseña.
"""
from django.contrib.auth.hashers import make_password
from django.db import migrations


def marcar_passwords_inutilizables(apps, schema_editor):
    User = apps.get_model("auth", "User")
    # make_password(None) genera el formato "!<aleatorio>" que Django reconoce
    # como inutilizable; los modelos históricos de las migraciones no traen
    # set_unusable_password(), por eso se usa el hasher directo.
    for user in User.objects.filter(password=""):
        user.password = make_password(None)
        user.save(update_fields=["password"])


def revertir(apps, schema_editor):
    # No se puede distinguir cuáles quedaron inutilizables por esta migración y
    # cuáles ya lo estaban, y volver a "" solo restauraría el estado ambiguo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0014_delete_verificationcode_and_more"),
    ]

    operations = [
        migrations.RunPython(marcar_passwords_inutilizables, revertir),
    ]
