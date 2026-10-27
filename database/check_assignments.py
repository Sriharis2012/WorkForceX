from database import SessionLocal, Employee

db = SessionLocal()
employees = db.query(Employee).filter(Employee.current_project_id != None).all()
for e in employees:
    print(e.name, "-> Project ID:", e.current_project_id)
db.close()