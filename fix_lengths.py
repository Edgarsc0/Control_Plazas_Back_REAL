import MySQLdb
db = MySQLdb.connect(host="168.231.73.222", user="omar.ramirez", passwd="Raal1011.", db="EjeCentral")
cursor = db.cursor()

tables = ["EMPLEADOS_COMPLETOS_SIG", "EMPLEADOS_COMPLETOS_SIG_STAGING", "EMPLEADOS_COMPLETOS_SIG_HISTORICO"]

for table in tables:
    try:
        cursor.execute(f"DESCRIBE {table}")
        columns = cursor.fetchall()
        for col in columns:
            name = col[0]
            type_ = col[1]
            if type_.startswith("varchar") and type_ != "varchar(255)":
                print(f"Altering {table}.`{name}` to varchar(255)")
                cursor.execute(f"ALTER TABLE {table} MODIFY `{name}` VARCHAR(255)")
        db.commit()
    except Exception as e:
        print(f"Error on {table}:", e)
print("Finished")
