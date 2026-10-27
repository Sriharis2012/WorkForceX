import sqlite3
conn = sqlite3.connect(r"..\database\workforce.db")
conn.execute("UPDATE employees SET rfid_uid = ? WHERE id = ?", ("1234", 1))
conn.commit()
conn.close()
print("done")
