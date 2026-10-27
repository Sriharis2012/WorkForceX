from database import SessionLocal, Employee, EmployeeSkill

db = SessionLocal()
db.query(EmployeeSkill).delete()
db.query(Employee).delete()
db.commit()
db.close()
print("All workers deleted!")
