import sqlite3
conn = sqlite3.connect('workforce.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(tables)