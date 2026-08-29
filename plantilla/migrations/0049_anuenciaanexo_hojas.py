# Un anexo pasa de ser UNA captura plana (filas + UA + justificación) a un
# LIBRO con N hojas, cada una con su propio cuadro de plazas, su Unidad
# Administrativa y su justificación (ver AnuenciaAnexo.hojas).
#
# Escrita a mano y no con `makemigrations` porque el autodetector lo propone
# como un rename `filas` -> `hojas`, que perdería el contenido: la forma del
# JSON cambia (una lista de FILAS pasa a ser una lista de HOJAS, cada una
# CONTENIENDO sus filas). El orden aquí es agregar -> migrar datos -> quitar,
# para que ningún anexo ya guardado se quede sin su contenido.

import uuid

from django.db import migrations, models


NOMBRE_HOJA_MIGRADA = "Hoja 1"


def a_hojas(apps, schema_editor):
    """Cada anexo existente se vuelve un libro de una sola hoja."""
    AnuenciaAnexo = apps.get_model("plantilla", "AnuenciaAnexo")
    for anexo in AnuenciaAnexo.objects.all().iterator():
        anexo.hojas = [
            {
                "_id": str(uuid.uuid4()),
                "nombre": NOMBRE_HOJA_MIGRADA,
                "unidad_administrativa": anexo.unidad_administrativa or "",
                "justificacion": anexo.justificacion or "",
                "filas": anexo.filas or [],
                "_unidades_detectadas": [],
            }
        ]
        anexo.save(update_fields=["hojas"])


def a_campos_planos(apps, schema_editor):
    """Reversa: se conserva SÓLO la primera hoja — es lo más que cabe en la
    estructura plana anterior. Un anexo con varias hojas perdería las demás,
    así que esta reversa sólo tiene sentido inmediatamente después de aplicar
    la migración, antes de que alguien capture un anexo multi-hoja."""
    AnuenciaAnexo = apps.get_model("plantilla", "AnuenciaAnexo")
    for anexo in AnuenciaAnexo.objects.all().iterator():
        primera = (anexo.hojas or [{}])[0]
        anexo.filas = primera.get("filas", [])
        anexo.unidad_administrativa = primera.get("unidad_administrativa", "")
        anexo.justificacion = primera.get("justificacion", "")
        anexo.save(update_fields=["filas", "unidad_administrativa", "justificacion"])


class Migration(migrations.Migration):

    dependencies = [
        ("plantilla", "0048_anuenciaanexo_nombre_archivo_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="anuenciaanexo",
            name="hojas",
            field=models.JSONField(default=list),
        ),
        migrations.RunPython(a_hojas, a_campos_planos),
        migrations.RemoveField(model_name="anuenciaanexo", name="filas"),
        migrations.RemoveField(model_name="anuenciaanexo", name="unidad_administrativa"),
        migrations.RemoveField(model_name="anuenciaanexo", name="justificacion"),
    ]
