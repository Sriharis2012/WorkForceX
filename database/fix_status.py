from database import SessionLocal, Employee

db = SessionLocal()
employees = db.query(Employee).all()
for e in employees:
    if e.availability == "Busy":
        e.availability = "On Project"
db.commit()
db.close()
print("Status terminology updated!")