from database import SessionLocal, EmployeeSkill

db = SessionLocal()
skills = db.query(EmployeeSkill).all()
for s in skills:
    print(s.employee_id, s.skill_name, s.skill_level)
db.close()