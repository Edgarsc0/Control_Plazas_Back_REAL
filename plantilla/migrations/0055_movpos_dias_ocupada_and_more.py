# Generated manually, mirroring 0044_movpos_fecha_ocupacion_and_more.py
#
# El schema YA fue aplicado a mano en las 3 tablas físicas (MOV_POS,
# MOV_POS_STAGING, MOV_POS_HISTORICO — ver alter_mov_pos_dias_ocupacion.sql
# en la raíz del repo) porque sp_dias_ocupacion_masivo necesitaba las
# columnas ya en producción. Aplicar esta migración con --fake:
#   python manage.py migrate plantilla 0055 --fake

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0054_anuenciaanexocambio'),
    ]

    operations = [
        migrations.AddField(
            model_name='movpos',
            name='dias_ocupada',
            field=models.IntegerField(blank=True, db_column='DIAS_OCUPADA', null=True),
        ),
        migrations.AddField(
            model_name='movpos',
            name='dias_vacante',
            field=models.IntegerField(blank=True, db_column='DIAS_VACANTE', null=True),
        ),
        migrations.AddField(
            model_name='movposhistorico',
            name='dias_ocupada',
            field=models.IntegerField(blank=True, db_column='DIAS_OCUPADA', null=True),
        ),
        migrations.AddField(
            model_name='movposhistorico',
            name='dias_vacante',
            field=models.IntegerField(blank=True, db_column='DIAS_VACANTE', null=True),
        ),
        migrations.AddField(
            model_name='movposstaging',
            name='dias_ocupada',
            field=models.IntegerField(blank=True, db_column='DIAS_OCUPADA', null=True),
        ),
        migrations.AddField(
            model_name='movposstaging',
            name='dias_vacante',
            field=models.IntegerField(blank=True, db_column='DIAS_VACANTE', null=True),
        ),
    ]
