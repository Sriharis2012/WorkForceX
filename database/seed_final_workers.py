import random
from database import SessionLocal, Employee, EmployeeSkill

random.seed(99)

first_names = ["Aravind", "Bhavya", "Chandran", "Farhan", "Gayathri", "Harish",
               "Indira", "Jagan", "Naveen", "Oviya", "Pranav", "Queenie", "Ravi",
               "Sandhya", "Tarun", "Uma", "Wilson", "Yamini", "Zara", "Chitra",
               "Dinesh", "Esha", "Fahim", "Gowtham", "Hema", "Iyappan", "Jothi", "Om"]

departments = ["IT", "QA", "HR", "Design", "DevOps"]
roles = {
    "IT": ["Frontend Developer", "Backend Developer", "Full Stack Developer", "Mobile Developer"],
    "QA": ["Test Engineer", "QA Lead"],
    "HR": ["HR Executive", "Recruiter"],
    "Design": ["UI Designer", "UX Designer"],
    "DevOps": ["DevOps Engineer", "Cloud Engineer"]
}

skill_pool = ["Python", "JavaScript", "React", "HTML", "CSS", "SQL", "FastAPI", "Django",
              "Node.js", "AWS", "Docker", "Kubernetes", "Testing", "Figma", "Java", "C++"]

availability_options = ["Available", "Available", "Available", "On Project", "On Project", "On Leave"]

db = SessionLocal()

start_num = 23  # continuing from EMP023 / RF023

for i in range(28):
    emp_num = start_num + i
    name = first_names[i % len(first_names)]
    dept = random.choice(departments)
    role = random.choice(roles[dept])
    availability = random.choice(availability_options)
    workload = 0 if availability == "Available" else random.randint(30, 90)
    performance = random.randint(65, 98)

    employee = Employee(
        employee_id=f"EMP{emp_num:03d}",
        rfid_uid=f"RF{emp_num:03d}",
        name=name,
        department=dept,
        role=role,
        availability=availability,
        workload=workload,
        performance_score=performance
    )
    db.add(employee)
    db.commit()

    num_skills = random.randint(3, 6)
    chosen_skills = random.sample(skill_pool, num_skills)
    for skill in chosen_skills:
        level = random.randint(50, 98)
        db.add(EmployeeSkill(employee_id=employee.id, skill_name=skill, skill_level=level))

db.commit()
db.close()
print("28 more workers added! Total should now be 50.")