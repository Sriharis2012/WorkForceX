from database import SessionLocal, EmployeeSkill

db = SessionLocal()

# Clear existing data
db.query(EmployeeSkill).delete()
db.commit()

# Add clean data
skills_data = [
    {"employee_id": 1, "skill_name": "HTML", "skill_level": 90},
    {"employee_id": 1, "skill_name": "CSS", "skill_level": 85},
    {"employee_id": 1, "skill_name": "JavaScript", "skill_level": 92},
    {"employee_id": 2, "skill_name": "HTML", "skill_level": 95},
    {"employee_id": 2, "skill_name": "CSS", "skill_level": 90},
    {"employee_id": 2, "skill_name": "JavaScript", "skill_level": 60},
]

for s in skills_data:
    db.add(EmployeeSkill(**s))

db.commit()
db.close()
print("Skills data cleaned and reseeded successfully!")