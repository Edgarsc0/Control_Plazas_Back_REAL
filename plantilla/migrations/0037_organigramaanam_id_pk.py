# Cambia la PK de ORGANIGRAMA_ANAM de `departamento` a un `id` autoincremental,
# y fusiona ORGANIGRAMA_ANAM_SIG dentro de ORGANIGRAMA_ANAM (isSIGInfo=1) —
# necesario porque un mismo `departamento` ahora puede existir en ambos
# conjuntos (institucional isSIGInfo=0 y snapshot SIG isSIGInfo=1). El DDL
# real (ALTER TABLE + INSERT) ya se corrió a mano en producción, por eso
# database_operations=[] — mismo patrón que 0024_adopt_organigrama_anam.py
# y 0029_organigramaanamsig.py.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plantilla', '0036_catcorreccion_auditoria'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='organigramaanam',
                    name='departamento',
                    field=models.CharField(max_length=255),
                ),
                migrations.AddField(
                    model_name='organigramaanam',
                    name='id',
                    field=models.BigAutoField(primary_key=True, serialize=False),
                ),
                migrations.AddConstraint(
                    model_name='organigramaanam',
                    constraint=models.UniqueConstraint(
                        fields=('departamento', 'isSIGInfo'),
                        name='uq_departamento_sig',
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
