from django.db import migrations, models


def add_id_registro_desicivo(apps, schema_editor):
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
                  AND COLUMN_NAME = 'idRegistroDesicivo'
                """,
                [db_name, table],
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    f"ALTER TABLE `{table}` ADD COLUMN `idRegistroDesicivo` BIGINT NULL"
                )


def remove_id_registro_desicivo(apps, schema_editor):
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
                  AND COLUMN_NAME = 'idRegistroDesicivo'
                """,
                [db_name, table],
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(
                    f"ALTER TABLE `{table}` DROP COLUMN `idRegistroDesicivo`"
                )


class Migration(migrations.Migration):

    dependencies = [
        ("plantilla", "0016_add_categoria_vacancia"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_id_registro_desicivo,
                    reverse_code=remove_id_registro_desicivo,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="movpos",
                    name="id_registro_desicivo",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idRegistroDesicivo",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposhistorico",
                    name="id_registro_desicivo",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idRegistroDesicivo",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposstaging",
                    name="id_registro_desicivo",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idRegistroDesicivo",
                        null=True,
                    ),
                ),
            ],
        ),
    ]
