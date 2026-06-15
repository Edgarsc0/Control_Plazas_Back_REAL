import MySQLdb
db = MySQLdb.connect(host="168.231.73.222", user="omar.ramirez", passwd="Raal1011.", db="EjeCentral")
cursor = db.cursor()

tables = ["EMPLEADOS_COMPLETOS_SIG", "EMPLEADOS_COMPLETOS_SIG_STAGING", "EMPLEADOS_COMPLETOS_SIG_HISTORICO"]
columns_to_text = ["UA Validación", "Validando de posición por documento", "Val_estatx", "NJ COMP", "NJ OK", "Columna", "nombreNJ", "NJOperativoComb"]

for table in tables:
    for col in columns_to_text:
        try:
            print(f"Altering {table}.`{col}` to TEXT")
            cursor.execute(f"ALTER TABLE {table} MODIFY `{col}` TEXT")
        except Exception as e:
            print(f"Error on {table}.{col}:", e)
    db.commit()

print("Finished")
