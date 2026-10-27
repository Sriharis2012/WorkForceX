"""
AIService — the single entry point the backend uses for anything
"AI". Internally it's rule-based scoring today (see scoring.py), but
every method here receives structured, pre-fetched data — never raw
DB dumps — so a cloud LLM provider can be swapped in later (see
CLOUD_PROVIDER below) without changing any caller.

AI failures must never break the hardware/attendance flow: every
public method catches its own exceptions and returns a safe fallback
dict with an "error" key rather than raising.
"""
import sys
import os
from datetime import datetime, date, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import SessionLocal, Employee, EmployeeSkill, Task, Project, TaskHistory, ProjectMember

from scoring import (
    employee_task_match_score,
    employee_task_allocation_score,
    rank_tasks_for_employee,
    skill_gap,
    workload_percentage,
    workload_label,
)

# Cloud provider is opt-in and never hardcoded. Set AI_PROVIDER=cloud
# and the relevant *_API_KEY in your .env once you have one; until
# then everything runs on the deterministic rule-based scorer above.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "rule_based")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _days_until(deadline_str):
    if not deadline_str:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d-%m-%Y"):
        try:
            d = datetime.strptime(deadline_str, fmt).date()
            return (d - date.today()).days
        except ValueError:
            continue
    return None


class AIService:

    def _employee_skill_map(self, db, employee_id):
        rows = db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == employee_id).all()
        return {r.skill_name: r.skill_level for r in rows}

    def _active_task_count(self, db, employee_id):
        return db.query(Task).filter(
            Task.assigned_employee_id == employee_id,
            Task.status.in_(["PENDING", "IN_PROGRESS"])
        ).count()

    def _get_employee_workload(self, db, employee_id):
        """Alias kept for Step 3 readability — same active-task count
        used everywhere else in this file."""
        return self._active_task_count(db, employee_id)

    def sync_employee_workload(self, db, employee_id):
        """
        Step 4: recompute Employee.workload from the current active
        (PENDING + IN_PROGRESS only — SUBMITTED/COMPLETED/BLOCKED are
        never "active") task count, using the exact same formula as
        the rest of the AI layer. Call this after any task status
        change that can affect active-task count (start, submit,
        block/unblock, verify approve/reject).

        Takes an existing session and does NOT commit — the caller
        (already inside its own status-change transaction) commits
        once at the end. Never raises: a sync failure shouldn't block
        the task-status change that triggered it.
        """
        try:
            if not employee_id:
                return
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            if emp is not None:
                emp.workload = workload_percentage(self._active_task_count(db, employee_id))
        except Exception:
            pass

    # ------------------------------------------------------------------
    def analyze_workload(self, employee_id):
        """Active/pending/completed/overdue task counts + workload %."""
        try:
            db = SessionLocal()
            all_tasks = db.query(Task).filter(Task.assigned_employee_id == employee_id).all()
            active = sum(1 for t in all_tasks if t.status in ("PENDING", "IN_PROGRESS"))
            pending = sum(1 for t in all_tasks if t.status == "PENDING")
            in_progress = sum(1 for t in all_tasks if t.status == "IN_PROGRESS")
            completed = sum(1 for t in all_tasks if t.status == "COMPLETED")
            overdue = sum(1 for t in all_tasks if t.status == "OVERDUE")
            blocked = sum(1 for t in all_tasks if t.status == "BLOCKED")
            wl_pct = workload_percentage(active)
            db.close()
            return {
                "employee_id": employee_id,
                "active_tasks": active,
                "pending_tasks": pending,
                "in_progress_tasks": in_progress,
                "completed_tasks": completed,
                "overdue_tasks": overdue,
                "blocked_tasks": blocked,
                "workload_percent": wl_pct,
                "workload_label": workload_label(wl_pct),
            }
        except Exception as e:
            return {"error": str(e), "workload_percent": 0, "workload_label": "Unknown"}

    # ------------------------------------------------------------------
    def match_employee_to_task(self, employee_id, task_id):
        """Skill-match score + ASSIGN/CONSIDER/AVOID for one employee+task pair."""
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                db.close()
                return {"error": "Task not found"}
            skills = self._employee_skill_map(db, employee_id)
            active_count = self._active_task_count(db, employee_id)
            days = _days_until(task.deadline)
            db.close()
            result = employee_task_match_score(
                skills, active_count,
                {
                    "required_skill": task.required_skill,
                    "required_skill_level": task.required_skill_level,
                    "priority": task.priority,
                },
                days_until_deadline=days,
            )
            result.update({"employee_id": employee_id, "task_id": task_id, "task_name": task.task_name})
            return result
        except Exception as e:
            return {"error": str(e), "recommendation": "AVOID", "reason": "AI evaluation failed"}

    # ------------------------------------------------------------------
    def recommend_task(self, employee_id):
        """
        Best unassigned/pending task for this employee across their
        current project, ranked by skill match + workload + priority +
        deadline urgency. Returns None (not an error) if there's simply
        nothing suitable to assign right now.
        """
        try:
            db = SessionLocal()
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                db.close()
                return {"error": "Employee not found"}

            skills = self._employee_skill_map(db, employee_id)
            active_count = self._active_task_count(db, employee_id)

            query = db.query(Task).filter(Task.status.in_(["PENDING", "IN_PROGRESS"]))
            if employee.current_project_id:
                query = query.filter(Task.project_id == employee.current_project_id)
            # Prefer tasks already assigned to this employee; fall back to
            # unassigned tasks on their project if they have none.
            candidates = query.filter(Task.assigned_employee_id == employee_id).all()
            if not candidates:
                candidates = query.filter(Task.assigned_employee_id.is_(None)).all()
            db.close()

            if not candidates:
                return {"employee_id": employee_id, "task": None, "message": "No suitable task available today"}

            candidate_dicts = [{
                "id": t.id, "task_name": t.task_name, "description": t.description,
                "required_skill": t.required_skill, "required_skill_level": t.required_skill_level,
                "priority": t.priority, "days_until_deadline": _days_until(t.deadline),
            } for t in candidates]

            ranked = rank_tasks_for_employee(skills, active_count, candidate_dicts)
            best = ranked[0]
            return {"employee_id": employee_id, "task": best}
        except Exception as e:
            return {"error": str(e), "task": None}

    # ------------------------------------------------------------------
    def generate_daily_task(self, employee_id, max_chars_per_line=16):
        """
        Short TFT-friendly version of recommend_task(): a 1-2 line
        summary that fits a 128x160 display. Falls back to a generic
        message on any AI failure so hardware never blocks on this.
        """
        rec = self.recommend_task(employee_id)
        task = rec.get("task") if isinstance(rec, dict) else None
        if not task:
            return {"employee_id": employee_id, "today_task": "No task assigned"}

        name = task["task_name"]
        words = name.split()
        line1, line2, cur = "", "", ""
        lines = []
        for w in words:
            if len((cur + " " + w).strip()) <= max_chars_per_line:
                cur = (cur + " " + w).strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        display_text = "\n".join(lines[:2])

        return {
            "employee_id": employee_id,
            "today_task": display_text,
            "task_id": task["id"],
            "full_task_name": name,
        }

    # ------------------------------------------------------------------
    def predict_skill_gap(self, employee_id, task_id):
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                db.close()
                return {"error": "Task not found"}
            skills = self._employee_skill_map(db, employee_id)
            db.close()
            gap = skill_gap(skills, task.required_skill, task.required_skill_level)
            return {"employee_id": employee_id, "task_id": task_id, "gap": gap}
        except Exception as e:
            return {"error": str(e), "gap": None}

    # ------------------------------------------------------------------
    def analyze_employee(self, employee_id):
        """Full digital-twin style snapshot for one employee."""
        try:
            db = SessionLocal()
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            if not employee:
                db.close()
                return {"error": "Employee not found"}
            skills = self._employee_skill_map(db, employee_id)
            completed = db.query(Task).filter(
                Task.assigned_employee_id == employee_id, Task.status == "COMPLETED"
            ).order_by(Task.completed_at.desc()).limit(5).all()
            recent_work = [t.task_name for t in completed]
            db.close()

            workload = self.analyze_workload(employee_id)

            return {
                "employee_id": employee.employee_id,
                "name": employee.name,
                "role": employee.role,
                "department": employee.department,
                "skills": skills,
                "current_project_id": employee.current_project_id,
                "current_project_name": employee.current_project_name,
                "workload_percent": workload.get("workload_percent"),
                "workload_label": workload.get("workload_label"),
                "active_tasks": workload.get("active_tasks"),
                "completed_tasks": workload.get("completed_tasks"),
                "overdue_tasks": workload.get("overdue_tasks"),
                "recent_completed_work": recent_work,
            }
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # STEP 3 — AI TEAM TASK ALLOCATION
    #
    # Assigns a distinct eligible PENDING task to each ACTIVE
    # ProjectMember of the project (the authoritative team relationship
    # — see _get_project_team below and database.ProjectMember), using
    # employee_task_allocation_score() — the same skill/workload/
    # priority/deadline signals as the rest of the AI layer, plus a
    # role-affinity nudge — so different specialists on a team land on
    # different, well-matched tasks instead of everyone competing for
    # the same one.
    #
    # Never touches IN_PROGRESS/COMPLETED/BLOCKED tasks, or PENDING
    # tasks that already have an owner — those are left exactly as an
    # explicit /tasks/{id}/assign or /tasks/{id}/status call left them.
    # ------------------------------------------------------------------

    def _get_project_team(self, db, project_id):
        """
        ProjectMember is the authoritative project<->employee relationship
        (Step 3 fix) — AI allocation reads the team from here, never from
        Employee.current_project_id/current_project_name, which remain on
        the Employee model only for backward compatibility with the
        existing dashboard/RFID display. Only ACTIVE memberships count.
        """
        member_rows = db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.status == "ACTIVE",
        ).all()
        employee_ids = [m.employee_id for m in member_rows]
        if not employee_ids:
            return []
        return db.query(Employee).filter(Employee.id.in_(employee_ids)).all()

    def _get_eligible_tasks(self, db, project_id):
        """Unassigned PENDING tasks on this project — the only tasks the
        allocator is allowed to touch (see class docstring above)."""
        return db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == "PENDING",
            Task.assigned_employee_id.is_(None),
        ).all()

    def _score_employee_task(self, skills, active_count, role, task_info):
        return employee_task_allocation_score(
            skills, active_count, role, task_info, task_info.get("days_until_deadline")
        )

    def _build_allocation(self, db, team, tasks):
        """
        Pure computation, no DB writes — used by both the preview
        endpoint and the real allocate endpoint, so identical inputs
        always produce an identical proposed allocation (Test 7:
        running allocation twice must be predictable/idempotent).
        """
        task_infos = [{
            "obj": t,
            "id": t.id,
            "task_name": t.task_name,
            "required_skill": t.required_skill,
            "required_skill_level": t.required_skill_level or 0,
            "priority": t.priority,
            "days_until_deadline": _days_until(t.deadline),
        } for t in tasks]

        # Score every (employee, task) pair up front.
        pairs = []
        for emp in team:
            skills = self._employee_skill_map(db, emp.id)
            active_count = self._get_employee_workload(db, emp.id)
            for tinfo in task_infos:
                score = self._score_employee_task(skills, active_count, emp.role, tinfo)
                # A task that explicitly requires a skill the employee has
                # zero record of is never proposed for that employee.
                if tinfo["required_skill"] and score["skill_match_percent"] == 0:
                    continue
                pairs.append((score["overall_score"], emp.id, tinfo["id"], emp, tinfo, score))

        # Deterministic greedy assignment: strongest match first; ties
        # broken by employee id then task id so repeated runs over the
        # same data always agree with each other.
        pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

        candidate_employee_ids = {p[1] for p in pairs}
        candidate_task_ids = {p[2] for p in pairs}

        assigned_employee_ids = set()
        assigned_task_ids = set()
        allocations = []

        for overall_score, emp_id, task_id, emp, tinfo, score in pairs:
            if emp_id in assigned_employee_ids or task_id in assigned_task_ids:
                continue
            assigned_employee_ids.add(emp_id)
            assigned_task_ids.add(task_id)
            allocations.append({
                "employee_db_id": emp.id,
                "employee_id": emp.employee_id,
                "employee_name": emp.name,
                "task_id": tinfo["id"],
                "task_name": tinfo["task_name"],
                "task_obj": tinfo["obj"],
                "score": score["overall_score"],
                "skill_match_percent": score["skill_match_percent"],
                "workload_percent": score["workload_percent"],
                "priority": tinfo["priority"],
                "deadline": tinfo["obj"].deadline,
                "reason": score["reason"],
            })

        unassigned_employees = []
        for emp in team:
            if emp.id in assigned_employee_ids:
                continue
            if emp.id not in candidate_employee_ids:
                reason = "No eligible unassigned project task matches this employee's skills."
            else:
                reason = "Eligible tasks were allocated to better-matching or less-loaded teammates."
            unassigned_employees.append({
                "employee_id": emp.employee_id,
                "employee_db_id": emp.id,
                "employee_name": emp.name,
                "status": "NO_TASK_AVAILABLE",
                "reason": reason,
            })

        unassigned_tasks = []
        for tinfo in task_infos:
            if tinfo["id"] in assigned_task_ids:
                continue
            if tinfo["id"] not in candidate_task_ids:
                reason = (f"No team member has the required skill '{tinfo['required_skill']}'."
                          if tinfo["required_skill"] else "No suitable team member found.")
            else:
                reason = "All qualified team members were assigned to higher-priority tasks."
            unassigned_tasks.append({
                "task_id": tinfo["id"],
                "task_name": tinfo["task_name"],
                "status": "UNASSIGNED",
                "reason": reason,
            })

        return allocations, unassigned_employees, unassigned_tasks

    def _apply_allocation(self, db, allocations, changed_by="AI_ALLOCATOR"):
        """
        Writes the proposed allocation to the DB: assigns each task
        (status stays PENDING — only /tasks/{id}/status ever changes
        status), records a TaskHistory row so the allocation is
        auditable, and syncs Employee.workload with the resulting
        active-task count using the same formula analyze_workload()
        already uses elsewhere.
        """
        now = _now_iso()
        touched_employee_ids = set()
        for a in allocations:
            task = a["task_obj"]
            old_status = task.status or "PENDING"
            task.assigned_employee_id = a["employee_db_id"]
            task.assigned_by = changed_by
            task.assigned_date = now
            if not task.status:
                task.status = "PENDING"
            task.updated_at = now

            db.add(TaskHistory(
                task_id=task.id,
                employee_id=a["employee_db_id"],
                old_status=old_status,
                new_status=task.status,
                old_progress=task.progress,
                new_progress=task.progress,
                changed_by=changed_by,
                notes=f"AI allocation (score {a['score']}): {a['reason']}",
                changed_at=now,
            ))
            touched_employee_ids.add(a["employee_db_id"])

        for emp_id in touched_employee_ids:
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            if emp is not None:
                emp.workload = workload_percentage(self._get_employee_workload(db, emp_id))

        db.commit()

    def allocate_project_tasks(self, project_id, dry_run=False):
        """
        Step 3 entry point.
          dry_run=False -> POST /ai/projects/{project_id}/allocate  (writes)
          dry_run=True  -> GET  /ai/projects/{project_id}/allocation-preview (read-only)

        Never raises: any internal failure is returned as
        {"error": True, "message": ..., "details": ...} so a bad
        allocation attempt can never take down the API or the RFID
        attendance flow.
        """
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {"error": True, "message": "AI allocation failed", "details": "Project not found"}

            team = self._get_project_team(db, project_id)
            if not team:
                return {
                    "project_id": project_id,
                    "project_name": project.project_name,
                    "preview": dry_run,
                    "allocations": [],
                    "unassigned_employees": [],
                    "unassigned_tasks": [],
                    "message": "No team members are assigned to this project yet.",
                }

            tasks = self._get_eligible_tasks(db, project_id)
            if not tasks:
                return {
                    "project_id": project_id,
                    "project_name": project.project_name,
                    "preview": dry_run,
                    "allocations": [],
                    "unassigned_employees": [{
                        "employee_id": e.employee_id,
                        "employee_db_id": e.id,
                        "employee_name": e.name,
                        "status": "NO_TASK_AVAILABLE",
                        "reason": "No eligible unassigned PENDING tasks on this project.",
                    } for e in team],
                    "unassigned_tasks": [],
                    "message": "No new eligible tasks to allocate.",
                }

            allocations, unassigned_employees, unassigned_tasks = self._build_allocation(db, team, tasks)

            if not dry_run and allocations:
                self._apply_allocation(db, allocations)

            clean_allocations = [
                {k: v for k, v in a.items() if k != "task_obj"} for a in allocations
            ]

            result = {
                "project_id": project_id,
                "project_name": project.project_name,
                "preview": dry_run,
                "allocations": clean_allocations,
                "unassigned_employees": unassigned_employees,
                "unassigned_tasks": unassigned_tasks,
            }
            if not clean_allocations:
                result["message"] = "No new eligible tasks to allocate."
            return result
        except Exception as e:
            db.rollback()
            return {"error": True, "message": "AI allocation failed", "details": str(e)}
        finally:
            db.close()


ai_service = AIService()
