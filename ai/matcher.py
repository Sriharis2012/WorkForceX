import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import SessionLocal, Employee, EmployeeSkill

def match_workers_for_task(required_skill, required_skill_level):
    db = SessionLocal()
    
    # Get all employees who have the required skill
    skill_matches = db.query(EmployeeSkill).filter(
        EmployeeSkill.skill_name == required_skill
    ).all()
    
    results = []
    for sm in skill_matches:
        employee = db.query(Employee).filter(Employee.id == sm.employee_id).first()
        if employee:
            skill_match_score = sm.skill_level
            availability_score = 100 if employee.availability == "Available" else 40
            workload_score = 100 - employee.workload
            
            overall_score = (skill_match_score * 0.5) + (availability_score * 0.3) + (workload_score * 0.2)
            
            results.append({
                "employee_name": employee.name,
                "skill_level": sm.skill_level,
                "availability": employee.availability,
                "workload": employee.workload,
                "overall_score": round(overall_score, 2)
            })
    
    db.close()
    results.sort(key=lambda x: x["overall_score"], reverse=True)
    return results

if __name__ == "__main__":
    matches = match_workers_for_task("JavaScript", 80)
    for m in matches:
        print(m)