from database import SessionLocal, Employee, EmployeeSkill

db = SessionLocal()

workers = [
    {"employee_id": "EMP003", "rfid_uid": "RF003", "name": "Karthick", "department": "IT", "role": "Backend Developer", "availability": "Available", "workload": 20, "performance_score": 88},
    {"employee_id": "EMP004", "rfid_uid": "RF004", "name": "Hanna Margaret", "department": "IT", "role": "Database Engineer", "availability": "Available", "workload": 10, "performance_score": 91},
    {"employee_id": "EMP005", "rfid_uid": "RF005", "name": "Evarose", "department": "QA", "role": "Test Engineer", "availability": "Available", "workload": 15, "performance_score": 85},
    {"employee_id": "EMP006", "rfid_uid": "RF006", "name": "Arjun", "department": "IT", "role": "Frontend Developer", "availability": "On Project", "workload": 60, "performance_score": 79},
    {"employee_id": "EMP007", "rfid_uid": "RF007", "name": "Divya", "department": "IT", "role": "Full Stack Developer", "availability": "Available", "workload": 5, "performance_score": 93},
]

skills_data = [
    {"employee_id": 3, "skill_name": "Python", "skill_level": 88},
    {"employee_id": 3, "skill_name": "FastAPI", "skill_level": 85},
    {"employee_id": 4, "skill_name": "SQL", "skill_level": 92},
    {"employee_id": 4, "skill_name": "Python", "skill_level": 75},
    {"employee_id": 5, "skill_name": "Testing", "skill_level": 90},
    {"employee_id": 6, "skill_name": "JavaScript", "skill_level": 82},
    {"employee_id": 6, "skill_name": "React", "skill_level": 78},
    {"employee_id": 7, "skill_name": "Python", "skill_level": 90},
    {"employee_id": 7, "skill_name": "JavaScript", "skill_level": 88},
    {"employee_id": 7, "skill_name": "React", "skill_level": 85},
]

for w in workers:
    db.add(Employee(**w))
db.commit()

for s in skills_data:
    db.add(EmployeeSkill(**s))
db.commit()

db.close()
print("5 new workers with skills added successfully!")