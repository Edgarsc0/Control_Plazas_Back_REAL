# Generated manually.
#
# La tabla ZAFIRO_TOLERANCIA_CONSULTA YA existe en la BD: la creó copia_back
# (PC Windows de Celery, misma BD) con su migración 0044. Por eso esta
# migración solo registra el modelo en el estado de Django
# (SeparateDatabaseAndState sin operaciones de BD): se aplica con un
# `migrate` normal, sin --fake.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plantilla", "0055_movpos_dias_ocupada_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ZafiroToleranciaConsulta",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        (
                            "consulta",
                            models.CharField(
                                choices=[
                                    ("posiciones", "Posiciones"),
                                    ("completos", "Empleados Completos"),
                                    ("bajas", "Empleados Bajas"),
                                    ("historial", "Historial Posición"),
                                    ("datos_personales", "Datos Personales"),
                                ],
                                max_length=32,
                                unique=True,
                            ),
                        ),
                        ("tolerancia_pct", models.DecimalField(decimal_places=2, max_digits=5)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("actualizado_por", models.CharField(blank=True, max_length=150, null=True)),
                    ],
                    options={
                        "db_table": "ZAFIRO_TOLERANCIA_CONSULTA",
                        "ordering": ["consulta"],
                        "managed": True,
                    },
                ),
            ],
        ),
    ]
