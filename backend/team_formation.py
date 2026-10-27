import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import SessionLocal, Employee, EmployeeSkill

def form_team(required_skills):
    """
    required_skills: list of skill names needed for the project
    Example: ["Python", "React", "SQL"]
    """
    db = SessionLocal()
    team = []
    assigned_employee_ids = set()

    for skill in required_skills:
        skill_matches = db.query(EmployeeSkill).filter(
            EmployeeSkill.skill_name == skill
        ).all()

        candidates = []
        for sm in skill_matches:
            if sm.employee_id in assigned_employee_ids:
                continue  # avoid assigning same person twice
            employee = db.query(Employee).filter(Employee.id == sm.employee_id).first()
            if not employee:
                continue
            skill_score = sm.skill_level
            availability_score = 100 if employee.availability == "Available" else 40
            workload_score = 100 - employee.workload
            overall_score = (skill_score * 0.5) + (availability_score * 0.3) + (workload_score * 0.2)
            candidates.append({
                "employee_id": employee.id,
                "name": employee.name,
                "role": employee.role,
                "skill": skill,
                "skill_level": sm.skill_level,
                "availability": employee.availability,
                "workload": employee.workload,
                "overall_score": round(overall_score, 2)
            })

        candidates.sort(key=lambda x: x["overall_score"], reverse=True)

        if candidates:
            best = candidates[0]
            team.append(best)
            assigned_employee_ids.add(best["employee_id"])
        else:
            team.append({
                "skill": skill,
                "name": None,
                "message": f"No available worker found for {skill}"
            })

    db.close()
    return team

if __name__ == "__main__":
    result = form_team(["Python", "React", "SQL", "Testing"])
    for r in result:
        print(r)