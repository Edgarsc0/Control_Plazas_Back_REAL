from django.db import migrations, models


def add_categoria_vacancia(apps, schema_editor):
    tables = ["MOV_POS", "MOV_POS_HISTORICO", "MOV_POS_STAGING"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        for table in tables:
            cursor.execute(
                """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND COLUMN_NAME = 'CATEGORIA_VACANCIA'
                """,
                [db_name, table],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    f"ALTER TABLE `{table}` ADD COLUMN `CATEGORIA_VACANCIA` VARCHAR(255) NULL"
                )


def remove_categoria_vacancia(apps, schema_editor):
    tables = ["MOV_POS", "MOV_POS_HISTORICO", "MOV_POS_STAGING"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        for table in tables:
            cursor.execute(
                """
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                  AND COLUMN_NAME = 'CATEGORIA_VACANCIA'
                """,
                [db_name, table],
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(
                    f"ALTER TABLE `{table}` DROP COLUMN `CATEGORIA_VACANCIA`"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("plantilla", "0015_bajassigstaging_idx_bajs_posicion_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_categoria_vacancia,
                    reverse_code=remove_categoria_vacancia,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="movpos",
                    name="categoria_vacancia",
                    field=models.CharField(
                        blank=True,
                        db_column="CATEGORIA_VACANCIA",
                        max_length=255,
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposhistorico",
                    name="categoria_vacancia",
                    field=models.CharField(
                        blank=True,
                        db_column="CATEGORIA_VACANCIA",
                        max_length=255,
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposstaging",
                    name="categoria_vacancia",
                    field=models.CharField(
                        blank=True,
                        db_column="CATEGORIA_VACANCIA",
                        max_length=255,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
