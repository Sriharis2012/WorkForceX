import random
from database import SessionLocal, Employee, EmployeeSkill

random.seed(42)

first_names = ["Aravind", "Bhavya", "Chandran", "Deepa", "Elango", "Farhan", "Gayathri", "Harish",
               "Indira", "Jagan", "Kavya", "Lokesh", "Meena", "Naveen", "Oviya", "Pranav",
               "Queenie", "Ravi", "Sandhya", "Tarun", "Uma", "Vignesh", "Wilson", "Yamini",
               "Zara", "Anitha", "Bala", "Chitra", "Dinesh", "Esha", "Fahim", "Gowtham",
               "Hema", "Iyappan", "Jothi", "Kumar", "Lakshmi", "Manoj", "Nithya", "Om",
               "Pavithra", "Rajesh", "Sneha", "Tanvi"]

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

last_id = db.query(Employee).count()

for i in range(43):
    emp_num = last_id + i + 1
    name = first_names[i % len(first_names)]
    dept = random.choice(departments)
    role = random.choice(roles[dept])
    availability = random.choice(availability_options)
    workload = 0 if availability == "Available" else random.randint(30, 90)
    performance = random.randint(65, 98)

    employee = Employee(
        employee_id=f"EMP{100+emp_num}",
        rfid_uid=f"RF{100+emp_num}",
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
print("43 additional workers added successfully! Total should now be 50.")