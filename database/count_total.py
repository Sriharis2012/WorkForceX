from database import SessionLocal, Employee

db = SessionLocal()
total = db.query(Employee).count()
print("Total employees:", total)
db.close()