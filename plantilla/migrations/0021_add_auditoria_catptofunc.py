# Ejecuta el DDL real (ALTER TABLE ADD COLUMN) de las columnas de auditoría
# `modificado_por`/`fecha_modificacion`:
#   - En las 3 tablas adoptadas en 0020 (cat_acciones, cat_acciones_motivos,
#     rc_cat_cod_presupuestal): el estado de Django ya las declara desde
#     0020 (via CreateModel), así que aquí solo se ejecuta la BD real
#     (`database_operations`, sin `state_operations`, para no duplicar el
#     estado).
#   - En CAT_PTO_FUNC (modelo ya existente desde 0004): AddField normal,
#     cambia estado y BD real juntos, como cualquier migración común.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0020_adopt_cat_acciones_motivos_presupuestal'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.AddField(
                    model_name='catacciones',
                    name='modificado_por',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='catacciones',
                    name='fecha_modificacion',
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
                migrations.AddField(
                    model_name='cataccionesmotivos',
                    name='modificado_por',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='cataccionesmotivos',
                    name='fecha_modificacion',
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
                migrations.AddField(
                    model_name='rccatcodpresupuestal',
                    name='modificado_por',
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
                migrations.AddField(
                    model_name='rccatcodpresupuestal',
                    name='fecha_modificacion',
                    field=models.DateTimeField(auto_now=True, null=True),
                ),
            ],
        ),
        migrations.AddField(
            model_name='catptofunc',
            name='fecha_modificacion',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='catptofunc',
            name='modificado_por',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
