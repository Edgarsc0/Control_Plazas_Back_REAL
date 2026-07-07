# Adopta 3 tablas legacy ya existentes en producción (cat_acciones,
# cat_acciones_motivos, rc_cat_cod_presupuestal), pobladas por el pipeline
# ZAFIRO y usadas por los SPs de post-proceso. Solo registra los modelos en
# el historial de Django (`state_operations`) sin ejecutar ningún DDL — las
# tablas y todas sus columnas ya existen tal cual. Las 2 columnas de
# auditoría nuevas se agregan en la siguiente migración (0021), ya con estos
# modelos presentes en el estado de Django (ahí sí corre el ALTER TABLE).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0019_movposlatest'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='CatAcciones',
                    fields=[
                        ('action', models.CharField(max_length=50, primary_key=True, serialize=False)),
                        ('action_description', models.CharField(blank=True, max_length=255, null=True)),
                        ('effective_status', models.CharField(blank=True, max_length=50, null=True)),
                        ('descripcion', models.TextField(blank=True, null=True)),
                        ('modificado_por', models.CharField(blank=True, max_length=255, null=True)),
                        ('fecha_modificacion', models.DateTimeField(auto_now=True, null=True)),
                    ],
                    options={
                        'db_table': 'cat_acciones',
                        'managed': True,
                    },
                ),
                migrations.CreateModel(
                    name='CatAccionesMotivos',
                    fields=[
                        ('id', models.AutoField(primary_key=True, serialize=False)),
                        ('accion', models.CharField(max_length=10)),
                        ('cd_motivo', models.CharField(max_length=10)),
                        ('descripcion', models.CharField(max_length=255)),
                        ('estado_efectivo', models.CharField(max_length=20)),
                        ('descripcion_larga', models.TextField(blank=True, null=True)),
                        ('modificado_por', models.CharField(blank=True, max_length=255, null=True)),
                        ('fecha_modificacion', models.DateTimeField(auto_now=True, null=True)),
                    ],
                    options={
                        'db_table': 'cat_acciones_motivos',
                        'managed': True,
                    },
                ),
                migrations.CreateModel(
                    name='RcCatCodPresupuestal',
                    fields=[
                        ('pk', models.CompositePrimaryKey('codigo_presupuestal', 'escala', blank=True, editable=False, primary_key=True, serialize=False)),
                        ('codigo_presupuestal', models.CharField(max_length=55)),
                        ('escala', models.SmallIntegerField()),
                        ('nivel', models.CharField(blank=True, max_length=55, null=True)),
                        ('smb', models.DecimalField(blank=True, decimal_places=2, max_digits=55, null=True)),
                        ('smn', models.DecimalField(blank=True, decimal_places=2, max_digits=55, null=True)),
                        ('nivel_jerarquico', models.CharField(blank=True, max_length=55, null=True)),
                        ('modificado_por', models.CharField(blank=True, max_length=255, null=True)),
                        ('fecha_modificacion', models.DateTimeField(auto_now=True, null=True)),
                    ],
                    options={
                        'db_table': 'rc_cat_cod_presupuestal',
                        'managed': True,
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
