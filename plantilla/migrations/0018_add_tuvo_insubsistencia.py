from django.db import migrations, models

COLUMNS = {
    "TUVO_INSUBSISTENCIA": "CHAR(1) NULL DEFAULT 'N'",
    "idInsubsistenciaDetectada": "BIGINT NULL",
}


def add_columns(apps, schema_editor):
    tables = ["MOV_POS", "MOV_POS_HISTORICO", "MOV_POS_STAGING"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        for table in tables:
            for column, ddl in COLUMNS.items():
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                    """,
                    [db_name, table, column],
                )
                if cursor.fetchone()[0] == 0:
                    cursor.execute(
                        f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl}"
                    )


def remove_columns(apps, schema_editor):
    tables = ["MOV_POS", "MOV_POS_HISTORICO", "MOV_POS_STAGING"]
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        for table in tables:
            for column in COLUMNS:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = %s
                      AND COLUMN_NAME = %s
                    """,
                    [db_name, table, column],
                )
                if cursor.fetchone()[0] > 0:
                    cursor.execute(
                        f"ALTER TABLE `{table}` DROP COLUMN `{column}`"
                    )


class Migration(migrations.Migration):

    dependencies = [
        ("plantilla", "0017_add_id_registro_desicivo"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_columns,
                    reverse_code=remove_columns,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="movpos",
                    name="tuvo_insubsistencia",
                    field=models.CharField(
                        blank=True,
                        db_column="TUVO_INSUBSISTENCIA",
                        max_length=1,
                        null=True,
                        default="N",
                    ),
                ),
                migrations.AddField(
                    model_name="movpos",
                    name="id_insubsistencia_detectada",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idInsubsistenciaDetectada",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposhistorico",
                    name="tuvo_insubsistencia",
                    field=models.CharField(
                        blank=True,
                        db_column="TUVO_INSUBSISTENCIA",
                        max_length=1,
                        null=True,
                        default="N",
                    ),
                ),
                migrations.AddField(
                    model_name="movposhistorico",
                    name="id_insubsistencia_detectada",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idInsubsistenciaDetectada",
                        null=True,
                    ),
                ),
                migrations.AddField(
                    model_name="movposstaging",
                    name="tuvo_insubsistencia",
                    field=models.CharField(
                        blank=True,
                        db_column="TUVO_INSUBSISTENCIA",
                        max_length=1,
                        null=True,
                        default="N",
                    ),
                ),
                migrations.AddField(
                    model_name="movposstaging",
                    name="id_insubsistencia_detectada",
                    field=models.BigIntegerField(
                        blank=True,
                        db_column="idInsubsistenciaDetectada",
                        null=True,
                    ),
                ),
            ],
        ),
    ]
