# Adopta la tabla legacy ORGANIGRAMA_ANAM (ya existente en producción,
# poblada por el pipeline ZAFIRO). Solo registra el modelo en el historial
# de Django (`state_operations`) sin ejecutar ningún DDL sobre las 9 columnas
# reales de la tabla. Las 2 columnas de auditoría nuevas se agregan en la
# siguiente migración (0025), ya con este modelo presente en el estado de
# Django (ahí sí corre el ALTER TABLE).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0023_add_nivel_jerarquico_prioridad_config'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='OrganigramaAnam',
                    fields=[
                        ('departamento', models.CharField(max_length=255, primary_key=True, serialize=False)),
                        ('unidad_negocio', models.CharField(max_length=255)),
                        ('estado_fecha_efectiva', models.CharField(max_length=255)),
                        ('descripcion_larga', models.CharField(max_length=500)),
                        ('nivel_direccion', models.CharField(blank=True, max_length=255, null=True)),
                        ('unidad_administrativa', models.CharField(max_length=255)),
                        ('doaf', models.CharField(max_length=255)),
                        ('num_posicion_gerente', models.CharField(max_length=255)),
                        ('posicion_director', models.CharField(max_length=255)),
                        ('modificado_por', models.CharField(blank=True, max_length=255, null=True)),
                        ('fecha_modificacion', models.DateTimeField(auto_now=True, null=True)),
                    ],
                    options={
                        'db_table': 'ORGANIGRAMA_ANAM',
                        'managed': True,
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
