from database import SessionLocal, Employee, EmployeeSkill

db = SessionLocal()

workers = [
    {"employee_id": "EMP008", "rfid_uid": "RF008", "name": "Ramesh", "department": "IT", "role": "DevOps Engineer", "availability": "Available", "workload": 10, "performance_score": 87},
    {"employee_id": "EMP009", "rfid_uid": "RF009", "name": "Sneha", "department": "IT", "role": "UI/UX Designer", "availability": "Available", "workload": 25, "performance_score": 90},
    {"employee_id": "EMP010", "rfid_uid": "RF010", "name": "Vignesh", "department": "IT", "role": "Backend Developer", "availability": "On Project", "workload": 75, "performance_score": 82},
    {"employee_id": "EMP011", "rfid_uid": "RF011", "name": "Meena", "department": "QA", "role": "QA Engineer", "availability": "Available", "workload": 15, "performance_score": 89},
    {"employee_id": "EMP012", "rfid_uid": "RF012", "name": "Suresh", "department": "IT", "role": "Cloud Engineer", "availability": "Available", "workload": 30, "performance_score": 85},
    {"employee_id": "EMP013", "rfid_uid": "RF013", "name": "Lakshmi", "department": "IT", "role": "Data Analyst", "availability": "Available", "workload": 20, "performance_score": 91},
    {"employee_id": "EMP014", "rfid_uid": "RF014", "name": "Prakash", "department": "IT", "role": "Frontend Developer", "availability": "On Project", "workload": 65, "performance_score": 80},
    {"employee_id": "EMP015", "rfid_uid": "RF015", "name": "Anitha", "department": "HR", "role": "HR Manager", "availability": "Available", "workload": 40, "performance_score": 88},
    {"employee_id": "EMP016", "rfid_uid": "RF016", "name": "Vinoth", "department": "IT", "role": "Full Stack Developer", "availability": "Available", "workload": 10, "performance_score": 93},
    {"employee_id": "EMP017", "rfid_uid": "RF017", "name": "Kavya", "department": "IT", "role": "Mobile Developer", "availability": "Available", "workload": 35, "performance_score": 86},
    {"employee_id": "EMP018", "rfid_uid": "RF018", "name": "Manoj", "department": "IT", "role": "Backend Developer", "availability": "On Project", "workload": 80, "performance_score": 78},
    {"employee_id": "EMP019", "rfid_uid": "RF019", "name": "Deepa", "department": "IT", "role": "Database Administrator", "availability": "Available", "workload": 20, "performance_score": 90},
    {"employee_id": "EMP020", "rfid_uid": "RF020", "name": "Ashwin", "department": "IT", "role": "Security Engineer", "availability": "Available", "workload": 15, "performance_score": 92},
    {"employee_id": "EMP021", "rfid_uid": "RF021", "name": "Priyanka", "department": "IT", "role": "Frontend Developer", "availability": "Available", "workload": 5, "performance_score": 94},
    {"employee_id": "EMP022", "rfid_uid": "RF022", "name": "Bala", "department": "IT", "role": "Systems Engineer", "availability": "On Project", "workload": 70, "performance_score": 81},
]

for w in workers:
    db.add(Employee(**w))
db.commit()

skills_data = [
    {"employee_id": 8, "skill_name": "Docker", "skill_level": 88}, {"employee_id": 8, "skill_name": "Kubernetes", "skill_level": 82},
    {"employee_id": 9, "skill_name": "Figma", "skill_level": 93}, {"employee_id": 9, "skill_name": "CSS", "skill_level": 87},
    {"employee_id": 10, "skill_name": "Python", "skill_level": 84}, {"employee_id": 10, "skill_name": "FastAPI", "skill_level": 80},
    {"employee_id": 11, "skill_name": "Testing", "skill_level": 91}, {"employee_id": 11, "skill_name": "Python", "skill_level": 70},
    {"employee_id": 12, "skill_name": "AWS", "skill_level": 89}, {"employee_id": 12, "skill_name": "Docker", "skill_level": 83},
    {"employee_id": 13, "skill_name": "SQL", "skill_level": 90}, {"employee_id": 13, "skill_name": "Python", "skill_level": 85},
    {"employee_id": 14, "skill_name": "JavaScript", "skill_level": 79}, {"employee_id": 14, "skill_name": "React", "skill_level": 75},
    {"employee_id": 15, "skill_name": "Management", "skill_level": 90},
    {"employee_id": 16, "skill_name": "Python", "skill_level": 91}, {"employee_id": 16, "skill_name": "JavaScript", "skill_level": 89}, {"employee_id": 16, "skill_name": "React", "skill_level": 87},
    {"employee_id": 17, "skill_name": "React Native", "skill_level": 86}, {"employee_id": 17, "skill_name": "JavaScript", "skill_level": 84},
    {"employee_id": 18, "skill_name": "Python", "skill_level": 77}, {"employee_id": 18, "skill_name": "SQL", "skill_level": 80},
    {"employee_id": 19, "skill_name": "SQL", "skill_level": 94}, {"employee_id": 19, "skill_name": "PostgreSQL", "skill_level": 88},
    {"employee_id": 20, "skill_name": "Security", "skill_level": 90}, {"employee_id": 20, "skill_name": "Python", "skill_level": 78},
    {"employee_id": 21, "skill_name": "JavaScript", "skill_level": 92}, {"employee_id": 21, "skill_name": "React", "skill_level": 90}, {"employee_id": 21, "skill_name": "CSS", "skill_level": 88},
    {"employee_id": 22, "skill_name": "Linux", "skill_level": 85}, {"employee_id": 22, "skill_name": "Python", "skill_level": 76},
]

for s in skills_data:
    db.add(EmployeeSkill(**s))
db.commit()

db.close()
print("15 more workers with skills added successfully!")