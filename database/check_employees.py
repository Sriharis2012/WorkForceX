from database import SessionLocal, Employee

db = SessionLocal()
employees = db.query(Employee).all()
for e in employees:
    print(e.id, e.employee_id, e.rfid_uid, e.name)
db.close()