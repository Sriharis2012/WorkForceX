from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import sys
import os
from typing import Any, Union, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import SessionLocal, Employee, EmployeeSkill, Task, Project, TaskHistory, Skill, Assignment, ProjectMember

app = FastAPI(title="Workforce Digital Twin API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
index_html_path = os.path.join(frontend_dir, 'index.html')
if os.path.exists(frontend_dir):
    app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="dashboard")

@app.get("/")
def home(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept and os.path.exists(index_html_path):
        return FileResponse(index_html_path)
    return {"message": "Workforce Digital Twin Backend is Running"}

@app.get("/employees")
def get_employees():
    db = SessionLocal()
    employees = db.query(Employee).all()
    db.close()
    return employees

from pydantic import BaseModel

class EmployeeCreate(BaseModel):
    employee_id: str
    rfid_uid: str
    name: str
    department: str
    role: str
    skills: Optional[list[Any]] = None

@app.post("/employees")
def add_employee(emp: EmployeeCreate):
    db = SessionLocal()
    existing_emp = db.query(Employee).filter(Employee.employee_id == emp.employee_id).first()
    if existing_emp:
        db.close()
        raise HTTPException(status_code=400, detail=f"Employee ID '{emp.employee_id}' is already registered")
    existing_rfid = db.query(Employee).filter(Employee.rfid_uid == emp.rfid_uid).first()
    if existing_rfid:
        db.close()
        raise HTTPException(status_code=400, detail=f"RFID UID '{emp.rfid_uid}' is already registered")
    try:
        new_emp = Employee(
            employee_id=emp.employee_id,
            rfid_uid=emp.rfid_uid,
            name=emp.name,
            department=emp.department,
            role=emp.role
        )
        db.add(new_emp)
        db.commit()
        db.refresh(new_emp)
        new_id = new_emp.id

        # If skills list provided, save to employee_skills
        if emp.skills:
            for sk in emp.skills:
                sk_name = sk.get("name") if isinstance(sk, dict) else str(sk)
                sk_lvl = sk.get("level", 80) if isinstance(sk, dict) else 80
                if sk_name:
                    db.add(EmployeeSkill(
                        employee_id=new_id,
                        skill_name=sk_name,
                        skill_level=sk_lvl
                    ))
            db.commit()

        db.close()
        return {"message": "Employee added successfully", "id": new_id}
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=400, detail=str(e))

from database import Skill

class SkillCreate(BaseModel):
    skill_name: str

@app.get("/skills")
def get_skills():
    db = SessionLocal()
    skills = db.query(Skill).all()
    db.close()
    return skills

@app.post("/skills")
def add_skill(skill: SkillCreate):
    db = SessionLocal()
    new_skill = Skill(skill_name=skill.skill_name)
    db.add(new_skill)
    db.commit()
    db.close()
    return {"message": "Skill added successfully"}

from database import Project

class ProjectCreate(BaseModel):
    project_name: str
    description: str
    priority: str
    deadline: str

@app.get("/projects")
def get_projects():
    db = SessionLocal()
    projects = db.query(Project).all()
    db.close()
    return projects

@app.post("/projects")
def add_project(project: ProjectCreate):
    db = SessionLocal()
    new_project = Project(
        project_name=project.project_name,
        description=project.description,
        priority=project.priority,
        deadline=project.deadline
    )
    db.add(new_project)
    db.commit()
    db.close()
    return {"message": "Project added successfully"}

from database import Task

class TaskCreate(BaseModel):
    project_id: int
    task_name: str
    description: str
    required_skill: str
    required_skill_level: int
    priority: str
    deadline: str

@app.get("/tasks")
def get_tasks():
    db = SessionLocal()
    tasks = db.query(Task).all()
    result = [_task_to_dict(t) for t in tasks]
    db.close()
    return result

@app.post("/tasks")
def add_task(task: TaskCreate):
    db = SessionLocal()
    new_task = Task(
        project_id=task.project_id,
        task_name=task.task_name,
        description=task.description,
        required_skill=task.required_skill,
        required_skill_level=task.required_skill_level,
        priority=task.priority,
        deadline=task.deadline
    )
    db.add(new_task)
    db.commit()
    db.close()
    return {"message": "Task added successfully"}

from database import EmployeeSkill

class EmployeeSkillCreate(BaseModel):
    employee_id: int
    skill_name: str
    skill_level: int

@app.get("/employee_skills")
def get_employee_skills():
    db = SessionLocal()
    data = db.query(EmployeeSkill).all()
    db.close()
    return data

@app.post("/employee_skills")
def add_employee_skill(es: EmployeeSkillCreate):
    db = SessionLocal()
    new_es = EmployeeSkill(
        employee_id=es.employee_id,
        skill_name=es.skill_name,
        skill_level=es.skill_level
    )
    db.add(new_es)
    db.commit()
    db.close()
    return {"message": "Employee skill added successfully"}

    import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai'))
from matcher import match_workers_for_task

@app.get("/match")
def get_matches(skill: str, level: int = 0):
    return match_workers_for_task(skill, level)

from database import Assignment

class AssignmentCreate(BaseModel):
    task_id: int
    employee_id: int
    employee_name: str
    skill_match_score: float

@app.get("/assignments")
def get_assignments():
    db = SessionLocal()
    data = db.query(Assignment).all()
    db.close()
    return data

@app.post("/assignments")
def approve_assignment(a: AssignmentCreate):
    db = SessionLocal()
    new_assignment = Assignment(
        task_id=a.task_id,
        employee_id=a.employee_id,
        employee_name=a.employee_name,
        skill_match_score=a.skill_match_score
    )
    db.add(new_assignment)
    db.commit()
    db.close()
    return {"message": "Assignment approved and saved"}

import sys
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ai'))
from team_formation import form_team

class TeamRequest(BaseModel):
    required_skills: list[str]

@app.post("/team-formation")
def get_team(request: TeamRequest):
    return form_team(request.required_skills)


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int):
    db = SessionLocal()
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        db.close()
        return {"error": "Employee not found"}
    db.delete(emp)
    db.commit()
    db.close()
    return {"message": "Employee removed successfully"}


class AddMemberRequest(BaseModel):
    employee_id: int


def _resolve_employee(db, employee_id_value):
    """Accepts either the numeric Employee.id or the human employee_id code
    (e.g. 'EMP001') — used by the project-member routes below."""
    emp = None
    try:
        emp = db.query(Employee).filter(Employee.id == int(employee_id_value)).first()
    except (ValueError, TypeError):
        pass
    if not emp:
        emp = db.query(Employee).filter(Employee.employee_id == str(employee_id_value)).first()
    return emp


class EmployeeUpdate(BaseModel):
    name: str
    department: str
    role: str

@app.put("/employees/{employee_id}")
def update_employee(employee_id: int, emp: EmployeeUpdate):
    db = SessionLocal()
    existing = db.query(Employee).filter(Employee.id == employee_id).first()
    if not existing:
        db.close()
        return {"error": "Employee not found"}
    existing.name = emp.name
    existing.department = emp.department
    existing.role = emp.role
    db.commit()
    db.close()
    return {"message": "Employee updated successfully"}


class ProjectMemberAdd(BaseModel):
    employee_id: Union[int, str]

ProjectMemberAdd.model_rebuild()

@app.post("/projects/{project_id}/members")
def add_project_member(project_id: int, member: ProjectMemberAdd):
    """
    Creates/reactivates the authoritative ProjectMember row (Step 3 fix)
    that AI allocation reads the team from. Employee.current_project_id/
    current_project_name are also updated here purely for backward
    compatibility with the existing dashboard/RFID display — they are
    NOT read by the AI allocator anymore.
    """
    db = SessionLocal()
    emp = _resolve_employee(db, member.employee_id)
    if not emp:
        db.close()
        return {"error": "Employee not found"}
    proj = db.query(Project).filter(Project.id == project_id).first()

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.employee_id == emp.id,
    ).first()
    if membership:
        membership.status = "ACTIVE"
        if not membership.joined_at:
            membership.joined_at = _now()
        if not membership.project_role:
            membership.project_role = emp.role
    else:
        db.add(ProjectMember(
            project_id=project_id,
            employee_id=emp.id,
            project_role=emp.role,
            joined_at=_now(),
            status="ACTIVE",
        ))

    # Backward-compat fields only — not the AI allocation source of truth.
    emp.availability = "On Project"
    emp.current_project_id = project_id
    if proj:
        emp.current_project_name = proj.project_name

    db.commit()
    db.close()
    return {"message": "Member added to project"}


@app.delete("/projects/{project_id}/members/{employee_id}")
def remove_project_member(project_id: int, employee_id: str):
    """
    Deactivates the ProjectMember row (status="ACTIVE" -> "REMOVED";
    rows are never deleted so history is preserved) and clears the
    backward-compat Employee.current_project_id/name fields if they
    pointed at this project.
    """
    db = SessionLocal()
    emp = _resolve_employee(db, employee_id)
    if not emp:
        db.close()
        return {"error": "Employee not found"}

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.employee_id == emp.id,
        ProjectMember.status == "ACTIVE",
    ).first()
    if membership:
        membership.status = "REMOVED"

    if emp.current_project_id == project_id:
        emp.availability = "Available"
        emp.current_project_id = None
        emp.current_project_name = None

    db.commit()
    db.close()
    return {"message": "Member removed from project"}

@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        db.close()
        return {"error": "Project not found"}
    
    # Unassign employees linked to this project (backward-compat field)
    employees = db.query(Employee).filter(Employee.current_project_id == project_id).all()
    for emp in employees:
        emp.current_project_id = None
        emp.current_project_name = None
        emp.availability = "Available"

    # Deactivate the authoritative ProjectMember rows for this project
    memberships = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    for m in memberships:
        m.status = "REMOVED"

    # Delete tasks linked to this project
    db.query(Task).filter(Task.project_id == project_id).delete()

    db.delete(project)
    db.commit()
    db.close()
    return {"message": "Project removed successfully"}


@app.get("/attendance/scan/{rfid_uid}")
def rfid_scan(rfid_uid: str):

    db = SessionLocal()

    employee = (
        db.query(Employee)
        .filter(Employee.rfid_uid == rfid_uid.upper())
        .first()
    )

    if not employee:
        db.close()

        return {
            "found": False,
            "access": False,
            "message": "Unknown RFID card"
        }

    project = None

    if employee.current_project_id:

        project = (
            db.query(Project)
            .filter(
                Project.id ==
                employee.current_project_id
            )
            .first()
        )

    project_progress = 0
    total_tasks = 0
    completed_tasks = 0

    if project:

        tasks = (
            db.query(Task)
            .filter(
                Task.project_id == project.id
            )
            .all()
        )

        total_tasks = len(tasks)

        completed_tasks = sum(
            1 for task in tasks
            if str(task.status).lower()
            in [
                "completed",
                "complete",
                "done"
            ]
        )

        if total_tasks > 0:
            project_progress = round(
                (
                    completed_tasks /
                    total_tasks
                ) * 100
            )

    performance = (
        employee.performance_score
        if employee.performance_score is not None
        else 0
    )

    result = {

        "found": True,

        "access": True,

        "employee": {

            "employee_id":
                employee.employee_id,

            "name":
                employee.name,

            "department":
                employee.department,

            "role":
                employee.role
        },

        "project": None,

        "performance":
            performance
    }

    if project:

        result["project"] = {

            "id":
                project.id,

            "name":
                project.project_name,

            "role":
                employee.role,

            "start_date":
                "N/A",

            "deadline":
                project.deadline,

            "progress":
                project_progress,

            "total_tasks":
                total_tasks,

            "completed_tasks":
                completed_tasks,

            "status":
                project.status
        }

    # ---- Step 4: current assigned task, for identification/display
    # only. RFID scanning is READ-ONLY — it never starts, updates,
    # submits, verifies, or completes a task; it only reports whatever
    # /tasks/{task_id}/status or /verify already set.
    current_task = _rfid_current_task(db, employee.id)
    result["task"] = current_task

    db.close()

    return result
# ==================================================
# TASK MANAGEMENT (status/history are explicit only —
# RFID scans never touch task status or progress)
# ==================================================

from datetime import datetime, timezone
from database import TaskHistory
from project_progress import calculate_project_progress, is_task_overdue
from ai_service import ai_service

VALID_TASK_STATUSES = {"PENDING", "IN_PROGRESS", "COMPLETED", "OVERDUE", "BLOCKED", "SUBMITTED"}

# Step 4: the worker task lifecycle.
#   PENDING -> IN_PROGRESS -> SUBMITTED -> COMPLETED
#   IN_PROGRESS <-> BLOCKED
#   SUBMITTED -> IN_PROGRESS (verification rejected)
# Only statuses that are keys here are constrained; a status outside
# this map (e.g. the legacy/unused "OVERDUE" literal, or no status
# at all) is left permissive so nothing pre-existing breaks. COMPLETED
# is a dead end via this endpoint on purpose — reaching COMPLETED is
# only ever allowed through PUT /tasks/{task_id}/verify.
TASK_TRANSITIONS = {
    "PENDING": {"IN_PROGRESS", "BLOCKED"},
    "IN_PROGRESS": {"SUBMITTED", "BLOCKED"},
    "BLOCKED": {"IN_PROGRESS"},
    "SUBMITTED": {"IN_PROGRESS"},
    "COMPLETED": set(),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _task_to_dict(task):
    """Serializes a Task row plus computed (never stored) fields like
    is_overdue. Used anywhere a task needs to go out over the API so
    the overdue flag is available without a stored OVERDUE status."""
    return {
        "id": task.id,
        "project_id": task.project_id,
        "task_name": task.task_name,
        "description": task.description,
        "required_skill": task.required_skill,
        "required_skill_level": task.required_skill_level,
        "priority": task.priority,
        "deadline": task.deadline,
        "assigned_employee_id": task.assigned_employee_id,
        "progress": task.progress,
        "status": task.status,
        "completed_at": task.completed_at,
        "assigned_date": task.assigned_date,
        "start_date": task.start_date,
        "assigned_by": task.assigned_by,
        "completion_notes": task.completion_notes,
        "evidence_url": task.evidence_url,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "is_overdue": is_task_overdue(task),
    }


def _rfid_current_task(db, employee_db_id):
    """
    Picks the single most relevant task to show on the RFID/TFT
    display for this employee: an active IN_PROGRESS task first, then
    a SUBMITTED one waiting on verification, then BLOCKED, then a
    not-yet-started PENDING one, then their most recently completed
    task, otherwise "no task assigned". Read-only — never mutates
    anything; called only from GET /attendance/scan/{rfid_uid}.
    """
    tasks = db.query(Task).filter(Task.assigned_employee_id == employee_db_id).all()
    if not tasks:
        return {"assigned": False, "display_status": "NO TASK ASSIGNED"}

    priority_order = ["IN_PROGRESS", "SUBMITTED", "BLOCKED", "PENDING"]
    chosen = None
    for status in priority_order:
        matches = [t for t in tasks if (t.status or "").upper() == status]
        if matches:
            # Most recently updated among ties.
            matches.sort(key=lambda t: t.updated_at or "", reverse=True)
            chosen = matches[0]
            break

    if chosen is None:
        completed = [t for t in tasks if (t.status or "").upper() == "COMPLETED"]
        if completed:
            completed.sort(key=lambda t: t.completed_at or "", reverse=True)
            chosen = completed[0]

    if chosen is None:
        return {"assigned": False, "display_status": "NO TASK ASSIGNED"}

    status_upper = (chosen.status or "").upper()
    display_status = {
        "IN_PROGRESS": "IN PROGRESS",
        "SUBMITTED": "WAITING VERIFICATION",
        "BLOCKED": "BLOCKED",
        "PENDING": "PENDING",
        "COMPLETED": "COMPLETED",
    }.get(status_upper, status_upper)

    return {
        "assigned": True,
        "task_id": chosen.id,
        "task_name": chosen.task_name,
        "status": chosen.status,
        "display_status": display_status,
        "progress": chosen.progress,
        "is_overdue": is_task_overdue(chosen),
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Single-task detail — used by the dashboard's 'View Submission'
    view (completion_notes/evidence_url) and anywhere the overdue flag
    or current progress/status of one task is needed."""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")
    result = _task_to_dict(task)
    db.close()
    return result


class TaskAssign(BaseModel):
    employee_id: int
    assigned_by: Optional[str] = None


@app.put("/tasks/{task_id}/assign")
def assign_task(task_id: int, body: TaskAssign):
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")

    employee = db.query(Employee).filter(Employee.id == body.employee_id).first()
    if not employee:
        db.close()
        raise HTTPException(status_code=404, detail="Employee not found")

    if (task.status or "").upper() == "COMPLETED":
        db.close()
        raise HTTPException(status_code=409, detail="Completed task cannot be reassigned")

    old_status = task.status
    task.assigned_employee_id = body.employee_id
    task.assigned_by = body.assigned_by
    task.assigned_date = _now()
    if not task.status:
        task.status = "PENDING"
    task.updated_at = _now()

    db.add(TaskHistory(
        task_id=task.id,
        employee_id=body.employee_id,
        old_status=old_status,
        new_status=task.status,
        old_progress=task.progress,
        new_progress=task.progress,
        changed_by=body.assigned_by,
        notes="Task assigned",
        changed_at=_now(),
    ))
    db.commit()
    db.close()
    return {"message": "Task assigned successfully"}


class TaskStatusUpdate(BaseModel):
    status: Optional[str] = None
    progress_percentage: Optional[int] = None
    completion_notes: Optional[str] = None
    # Optional evidence/result reference for a SUBMITTED task (a URL,
    # GitHub link, file path, etc). Never required — submitting with
    # only completion_notes describing the result is fully supported.
    evidence_url: Optional[str] = None
    changed_by: Optional[str] = None


@app.put("/tasks/{task_id}/status")
def update_task_status(task_id: int, body: TaskStatusUpdate):
    """
    Covers start / update-progress / submit / block / unblock.
    This is the ONLY place task status or progress changes apart from
    /tasks/{task_id}/verify — RFID scanning never calls either. Every
    change is written to task_history so completed work stays
    auditable; nothing is ever deleted.

    COMPLETED is intentionally unreachable from here: a task can only
    become COMPLETED via PUT /tasks/{task_id}/verify (approved=true),
    and once COMPLETED it is locked — this endpoint refuses to change
    a completed task at all, so it can never be silently overwritten.
    """
    if body.status and body.status.upper() not in VALID_TASK_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(VALID_TASK_STATUSES)}"
        )
    if body.progress_percentage is not None and not (0 <= body.progress_percentage <= 100):
        raise HTTPException(status_code=400, detail="progress_percentage must be 0-100")

    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = (task.status or "PENDING").upper()

    if old_status == "COMPLETED":
        db.close()
        raise HTTPException(
            status_code=409,
            detail="Task is COMPLETED and is locked; it cannot be modified further."
        )

    new_status = old_status
    if body.status:
        new_status = body.status.upper()
        if new_status == "COMPLETED":
            db.close()
            raise HTTPException(
                status_code=400,
                detail="Tasks can only be completed via PUT /tasks/{task_id}/verify with approved=true."
            )
        if new_status != old_status:
            allowed = TASK_TRANSITIONS.get(old_status)
            if allowed is not None and new_status not in allowed:
                db.close()
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid transition: {old_status} -> {new_status}. "
                           f"Allowed from {old_status}: {sorted(allowed) or 'none'}."
                )

    old_progress = task.progress

    if body.status:
        if old_status != "IN_PROGRESS" and new_status == "IN_PROGRESS" and not task.start_date:
            task.start_date = _now()
        task.status = new_status

    if body.progress_percentage is not None:
        task.progress = body.progress_percentage

    if body.completion_notes:
        task.completion_notes = body.completion_notes

    if body.evidence_url:
        task.evidence_url = body.evidence_url

    task.updated_at = _now()

    db.add(TaskHistory(
        task_id=task.id,
        employee_id=task.assigned_employee_id,
        old_status=old_status,
        new_status=task.status,
        old_progress=old_progress,
        new_progress=task.progress,
        changed_by=body.changed_by,
        notes=body.completion_notes,
        changed_at=_now(),
    ))

    # Active-task count (PENDING+IN_PROGRESS) can change on start,
    # submit, block, and unblock — keep Employee.workload in sync.
    if task.assigned_employee_id:
        ai_service.sync_employee_workload(db, task.assigned_employee_id)

    db.commit()

    # Snapshot the fields the response needs while `task` is still
    # attached to this session. db.commit() above expires task's
    # attributes (expire_on_commit=True), and db.close() right after
    # detaches the instance entirely — reading task.status/task.progress
    # after that point is what caused the DetachedInstanceError.
    response_status = task.status
    response_progress = task.progress

    db.close()
    return {"message": "Task updated successfully", "status": response_status, "progress": response_progress}


class TaskVerify(BaseModel):
    approved: bool
    verified_by: Optional[str] = None
    notes: Optional[str] = None


@app.put("/tasks/{task_id}/verify")
def verify_task(task_id: int, body: TaskVerify):
    """
    Manager/AI verification of a SUBMITTED task — the ONLY path a task
    can reach COMPLETED. RFID scanning never calls this.

      approved=true  -> SUBMITTED -> COMPLETED (progress=100, completed_at set)
      approved=false -> SUBMITTED -> IN_PROGRESS (worker continues; nothing marked complete)

    completion_notes/evidence_url from the original submission are
    left untouched either way.
    """
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        db.close()
        raise HTTPException(status_code=404, detail="Task not found")

    current_status = (task.status or "").upper()
    if current_status != "SUBMITTED":
        db.close()
        raise HTTPException(
            status_code=400,
            detail=f"Only a SUBMITTED task can be verified (current status: {current_status})."
        )

    old_status = task.status
    old_progress = task.progress

    if body.approved:
        task.status = "COMPLETED"
        task.progress = 100
        task.completed_at = _now()
        default_notes = "Verified and approved"
    else:
        task.status = "IN_PROGRESS"
        default_notes = "Verification rejected — returned to worker"

    task.updated_at = _now()

    db.add(TaskHistory(
        task_id=task.id,
        employee_id=task.assigned_employee_id,
        old_status=old_status,
        new_status=task.status,
        old_progress=old_progress,
        new_progress=task.progress,
        changed_by=body.verified_by,
        notes=body.notes or default_notes,
        changed_at=_now(),
    ))

    if task.assigned_employee_id:
        ai_service.sync_employee_workload(db, task.assigned_employee_id)

    db.commit()

    # Snapshot the fields the response needs while `task` is still
    # attached to this session — same DetachedInstanceError cause as
    # update_task_status: db.commit() expires task's attributes and
    # db.close() right after detaches the instance, so reading them
    # afterward fails.
    response_status = task.status
    response_progress = task.progress
    response_completed_at = task.completed_at

    db.close()
    return {
        "message": "Task verified and completed" if body.approved else "Task submission rejected",
        "status": response_status,
        "progress": response_progress,
        "completed_at": response_completed_at,
    }


@app.get("/tasks/{task_id}/history")
def get_task_history(task_id: int):
    db = SessionLocal()
    rows = db.query(TaskHistory).filter(TaskHistory.task_id == task_id).order_by(TaskHistory.changed_at).all()
    db.close()
    return rows


@app.get("/projects/{project_id}/progress")
def get_project_progress(project_id: int):
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        db.close()
        raise HTTPException(status_code=404, detail="Project not found")
    result = calculate_project_progress(db, project_id)
    db.close()
    return result


# ==================================================
# AI SERVICE LAYER
# Every route here calls AIService, which never raises —
# on internal failure it returns {"error": ...} so hardware
# and dashboard callers can handle it gracefully instead of
# getting a 500.
# ==================================================

from ai_service import ai_service


@app.get("/ai/employee/{employee_id}/analyze")
def ai_analyze_employee(employee_id: int):
    """Digital-twin snapshot: skills, workload, recent completed work."""
    return ai_service.analyze_employee(employee_id)


@app.get("/ai/digital-twin/{employee_id}")
def ai_digital_twin(employee_id: int):
    return ai_service.analyze_employee(employee_id)


@app.get("/ai/workload/{employee_id}")
def ai_workload(employee_id: int):
    return ai_service.analyze_workload(employee_id)


@app.get("/ai/match/{employee_id}/{task_id}")
def ai_match(employee_id: int, task_id: int):
    """Skill Match %, Workload, AI Recommendation, Reason for one pairing."""
    return ai_service.match_employee_to_task(employee_id, task_id)


@app.get("/ai/recommend-task/{employee_id}")
def ai_recommend_task(employee_id: int):
    """Best-fit pending/in-progress task for this employee right now."""
    return ai_service.recommend_task(employee_id)


@app.get("/ai/daily-task/{employee_id}")
def ai_daily_task(employee_id: int):
    """Short TFT-ready 'TODAY'S TASK' text — this is what ESP32/STM32 should call."""
    return ai_service.generate_daily_task(employee_id)


@app.get("/ai/skill-gap/{employee_id}/{task_id}")
def ai_skill_gap(employee_id: int, task_id: int):
    return ai_service.predict_skill_gap(employee_id, task_id)


# ---- STEP 3: AI TEAM TASK ALLOCATION -------------------------------
# Assigns each ACTIVE ProjectMember of the project (the authoritative
# team relationship — see database.ProjectMember) a distinct eligible
# PENDING task, using skills, role, workload, priority and deadline
# urgency. Never reassigns IN_PROGRESS/COMPLETED/BLOCKED work or
# PENDING tasks that already have an owner — see
# AIService.allocate_project_tasks() for the full rules. Like every
# other /ai/ route, this never raises; a failure comes back as a plain
# {"error": true, ...} JSON body instead of a 500.

@app.post("/ai/projects/{project_id}/allocate")
def ai_allocate_project_tasks(project_id: int):
    """Runs allocation and WRITES the result (task assignment + task
    history + workload sync). Safe to call repeatedly — once there is
    nothing new and eligible to allocate it returns a
    'No new eligible tasks to allocate' message instead of touching
    anything already assigned."""
    return ai_service.allocate_project_tasks(project_id, dry_run=False)


@app.get("/ai/projects/{project_id}/allocation-preview")
def ai_allocation_preview(project_id: int):
    """Identical computation to /allocate but READ-ONLY — no task,
    history, or workload changes. Lets the dashboard show 'AI
    Recommended Allocation' before a manager approves it."""
    return ai_service.allocate_project_tasks(project_id, dry_run=True)


@app.get("/task_history")
def get_all_task_history():
    """Returns the complete audit log of task changes for the History page."""
    db = SessionLocal()
    histories = db.query(TaskHistory).order_by(TaskHistory.changed_at.desc()).all()
    tasks = {t.id: t for t in db.query(Task).all()}
    employees = {e.id: e for e in db.query(Employee).all()}
    projects = {p.id: p for p in db.query(Project).all()}

    result = []
    for h in histories:
        task = tasks.get(h.task_id)
        emp = employees.get(h.employee_id) or (employees.get(task.assigned_employee_id) if task else None)
        proj = projects.get(task.project_id) if task else None
        result.append({
            "id": h.id,
            "task_id": h.task_id,
            "task_name": task.task_name if task else f"Task #{h.task_id}",
            "employee_id": h.employee_id,
            "employee_code": emp.employee_id if emp else None,
            "employee_name": emp.name if emp else "Unassigned",
            "project_id": proj.id if proj else None,
            "project_name": proj.project_name if proj else "Unassigned",
            "old_status": h.old_status,
            "new_status": h.new_status,
            "old_progress": h.old_progress,
            "new_progress": h.new_progress,
            "changed_by": h.changed_by or "System",
            "notes": h.notes,
            "changed_at": h.changed_at
        })
    db.close()
    return result


@app.get("/ai/workloads")
def get_all_workloads():
    """Batch workload analytics for all employees to power the Workload page efficiently."""
    db = SessionLocal()
    employees = db.query(Employee).all()
    db.close()
    results = []
    for emp in employees:
        analysis = ai_service.analyze_workload(emp.id)
        analysis.update({
            "employee_db_id": emp.id,
            "employee_id": emp.employee_id,
            "name": emp.name,
            "department": emp.department,
            "role": emp.role,
            "availability": emp.availability,
            "current_project_id": emp.current_project_id,
            "current_project_name": emp.current_project_name,
        })
        results.append(analysis)
    return results


@app.get("/ai/allocations")
def get_ai_allocations():
    """
    Evaluates real pending/in-progress tasks against employee skill sets,
    workloads, priority, and deadlines to provide genuine AI recommendations.
    Used on the dedicated AI Allocation page for Manager Review & Approval.
    """
    db = SessionLocal()
    tasks = db.query(Task).order_by(Task.deadline).all()
    employees = db.query(Employee).all()
    projects = {p.id: p for p in db.query(Project).all()}

    allocations = []
    for task in tasks:
        proj = projects.get(task.project_id)
        candidates = []
        for emp in employees:
            match_info = ai_service.match_employee_to_task(emp.id, task.id)
            if not match_info.get("error"):
                candidates.append({
                    "employee_id": emp.id,
                    "employee_code": emp.employee_id,
                    "name": emp.name,
                    "department": emp.department,
                    "role": emp.role,
                    "availability": emp.availability,
                    "skill_match_percent": match_info.get("skill_match_percent", 0),
                    "workload_percent": match_info.get("workload_percent", 0),
                    "workload_label": match_info.get("workload_label", "Unknown"),
                    "overall_score": match_info.get("overall_score", 0),
                    "recommendation": match_info.get("recommendation", "AVOID"),
                    "reason": match_info.get("reason", "")
                })
        candidates.sort(key=lambda x: x["overall_score"], reverse=True)
        best = candidates[0] if candidates else None

        assigned_emp = None
        if task.assigned_employee_id:
            for emp in employees:
                if emp.id == task.assigned_employee_id:
                    assigned_emp = {
                        "id": emp.id,
                        "employee_id": emp.employee_id,
                        "name": emp.name,
                        "role": emp.role
                    }
                    break

        allocations.append({
            "task_id": task.id,
            "task_name": task.task_name,
            "description": task.description,
            "project_id": task.project_id,
            "project_name": proj.project_name if proj else "Unassigned",
            "required_skill": task.required_skill,
            "required_skill_level": task.required_skill_level,
            "priority": task.priority,
            "deadline": task.deadline,
            "status": task.status,
            "progress": task.progress,
            "assigned_employee": assigned_emp,
            "recommended_employee": best,
            "alternatives": candidates[1:6] if len(candidates) > 1 else []
        })
    db.close()
    return allocations







