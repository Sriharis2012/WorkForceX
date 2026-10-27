import sqlite3

conn = sqlite3.connect('workforce.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE employees ADD COLUMN current_project_id INTEGER")
    print("Added current_project_id")
except Exception as e:
    print("current_project_id:", e)

try:
    cursor.execute("ALTER TABLE employees ADD COLUMN current_project_name TEXT")
    print("Added current_project_name")
except Exception as e:
    print("current_project_name:", e)

conn.commit()
conn.close()
print("Done!")