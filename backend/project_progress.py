"""
Project progress is always derived from task progress, never stored or
hardcoded. Import calculate_project_progress() wherever a project's
completion percentage/status needs to be shown.
"""
import sys
import os
from datetime import date, datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import Task


def _parse_deadline_date(deadline_str):
    """Best-effort parse of a task/project deadline string. Returns
    None (never raises) if the format isn't recognized, so overdue
    detection degrades to 'not overdue' instead of erroring."""
    if not deadline_str:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(deadline_str), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def is_task_overdue(task, today=None):
    """
    A task is overdue when its deadline has passed and it is not
    COMPLETED. This is always a *computed* flag — it never writes to
    task.status, so a COMPLETED task can never be silently overwritten
    and nothing needs a background job to "expire" tasks.
    """
    if (task.status or "").upper() == "COMPLETED":
        return False
    d = _parse_deadline_date(task.deadline)
    if d is None:
        return False
    return d < (today or date.today())


def calculate_project_progress(db, project_id):
    """
    Returns:
        {
          "progress_percentage": float,   # 0-100, avg of task.progress
          "task_count": int,
          "completed": int,
          "in_progress": int,
          "pending": int,
          "overdue": int,
          "blocked": int,
        }
    A project with zero tasks reports 0% rather than erroring, so the
    dashboard can still render it.
    """
    tasks = db.query(Task).filter(Task.project_id == project_id).all()

    if not tasks:
        return {
            "progress_percentage": 0,
            "task_count": 0,
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "overdue": 0,
            "blocked": 0,
        }

    total_progress = sum((t.progress or 0) for t in tasks)
    progress_percentage = round(total_progress / len(tasks), 1)

    def count(status):
        return sum(1 for t in tasks if (t.status or "").upper() == status)

    return {
        "progress_percentage": progress_percentage,
        "task_count": len(tasks),
        "completed": count("COMPLETED"),
        "in_progress": count("IN_PROGRESS"),
        "pending": count("PENDING"),
        "submitted": count("SUBMITTED"),
        # Overdue is computed from deadline-vs-today (see is_task_overdue),
        # not from a stored "OVERDUE" status, so it's always accurate
        # without any background job or risk of overwriting COMPLETED.
        "overdue": sum(1 for t in tasks if is_task_overdue(t)),
        "blocked": count("BLOCKED"),
    }
