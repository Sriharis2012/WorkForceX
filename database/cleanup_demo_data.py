from database import SessionLocal, Employee, EmployeeSkill

db = SessionLocal()

# Names to KEEP
keep_names = ["Gokul", "Hanna Margaret", "Karthick", "Evarose"]

all_employees = db.query(Employee).all()
removed_count = 0

for emp in all_employees:
    if emp.name not in keep_names:
        # remove their skills first
        db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == emp.id).delete()
        db.delete(emp)
        removed_count += 1

db.commit()
db.close()
print(f"Removed {removed_count} demo workers. Kept: {keep_names}")
