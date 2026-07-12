# Ejecuta el DDL real (ALTER TABLE ADD COLUMN) de las columnas de auditoría
# `modificado_por`/`fecha_modificacion` sobre ORGANIGRAMA_ANAM. El estado de
# Django ya las declara desde 0024 (vía CreateModel), así que aquí solo se
# ejecuta la BD real (`database_operations`, sin `state_operations`, para no
# duplicar el estado).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0024_adopt_organigrama_anam'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.AddField(
                    model_name='organigramaanam',
                    name='modificado_por',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='organigramaanam',
                    name='fecha_modificacion',
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
            ],
        ),
    ]
