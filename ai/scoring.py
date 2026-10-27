"""
Pure scoring functions for WorkforceX's AI layer.

Deliberately DB-independent: every function here takes plain dicts/lists
and numbers, so it can be unit-tested without SQLAlchemy and swapped
out later if the scoring logic needs to change (e.g. once a cloud LLM
is wired in via AIService, these remain the deterministic fallback).
"""

STATUS_ACTIVE = {"PENDING", "IN_PROGRESS"}
STATUS_DONE = {"COMPLETED"}


def _normalize_skills(employee_skills):
    """Case-insensitive lookup: your skills table and task.required_skill
    aren't guaranteed to share casing (e.g. 'PYTHON' vs 'Python'), so we
    match on the upper-cased skill name everywhere."""
    return {str(k).strip().upper(): v for k, v in employee_skills.items()}


def skill_match_percentage(employee_skills, required_skill, required_level):
    """
    employee_skills: dict {skill_name: skill_level (0-100)}
    Returns 0-100. No matching skill at all => 0.
    Matching is case-insensitive.
    """
    if not required_skill:
        return 0.0
    normalized = _normalize_skills(employee_skills)
    level = normalized.get(str(required_skill).strip().upper())
    if level is None:
        return 0.0
    if required_level <= 0:
        return 100.0
    # Employee can exceed the required level; cap at 100.
    return round(min(100.0, (level / required_level) * 100), 1)


def workload_percentage(active_task_count, max_reasonable_tasks=5):
    """
    Rough workload estimate from how many active (PENDING/IN_PROGRESS)
    tasks an employee is currently carrying. Caps at 100.
    """
    if max_reasonable_tasks <= 0:
        return 100.0
    return round(min(100.0, (active_task_count / max_reasonable_tasks) * 100), 1)


def workload_label(workload_pct):
    if workload_pct < 40:
        return "Low"
    if workload_pct < 75:
        return "Medium"
    return "High"


def deadline_urgency_score(days_until_deadline):
    """
    Higher score = more urgent. Overdue or same-day => 100.
    Scales down linearly, floors at 0 past 30 days out.
    """
    if days_until_deadline is None:
        return 50.0  # unknown deadline, treat as medium urgency
    if days_until_deadline <= 0:
        return 100.0
    if days_until_deadline >= 30:
        return 0.0
    return round(100 - (days_until_deadline / 30) * 100, 1)


PRIORITY_WEIGHT = {"HIGH": 100, "MEDIUM": 60, "LOW": 30}


def priority_score(priority):
    return PRIORITY_WEIGHT.get((priority or "").upper(), 50)


def employee_task_match_score(employee_skills, active_task_count, task, days_until_deadline=None):
    """
    Combined score used both for "recommend a task to this employee"
    and "recommend an employee for this task". Weights:
      skill match 45%, availability/workload 25%, priority 15%, urgency 15%
    task: dict with required_skill, required_skill_level, priority
    Returns dict with the breakdown, so the "Reason" column in the
    dashboard can be built directly from it.
    """
    skill_pct = skill_match_percentage(
        employee_skills, task.get("required_skill"), task.get("required_skill_level", 0)
    )
    workload_pct = workload_percentage(active_task_count)
    availability_score = round(100 - workload_pct, 1)
    prio_score = priority_score(task.get("priority"))
    urgency = deadline_urgency_score(days_until_deadline)

    overall = round(
        skill_pct * 0.45 + availability_score * 0.25 + prio_score * 0.15 + urgency * 0.15,
        1,
    )

    if skill_pct == 0:
        recommendation = "AVOID"
        reason = "No matching skill on record for this task."
    elif overall >= 75:
        recommendation = "ASSIGN"
        reason = f"Strong skill match ({skill_pct}%) with workload at {workload_pct}%."
    elif overall >= 50:
        recommendation = "CONSIDER"
        reason = f"Moderate skill match ({skill_pct}%); workload {workload_label(workload_pct)}."
    else:
        recommendation = "AVOID"
        reason = f"Weak fit — skill match {skill_pct}%, workload {workload_label(workload_pct)}."

    return {
        "skill_match_percent": skill_pct,
        "workload_percent": workload_pct,
        "workload_label": workload_label(workload_pct),
        "priority_score": prio_score,
        "urgency_score": urgency,
        "overall_score": overall,
        "recommendation": recommendation,
        "reason": reason,
    }


def rank_tasks_for_employee(employee_skills, active_task_count, candidate_tasks):
    """
    candidate_tasks: list of dicts, each with at least
      id, task_name, required_skill, required_skill_level, priority,
      and optionally days_until_deadline.
    Returns the same list annotated with match scores, sorted best-first.
    """
    scored = []
    for t in candidate_tasks:
        score = employee_task_match_score(
            employee_skills, active_task_count, t, t.get("days_until_deadline")
        )
        scored.append({**t, **score})
    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    return scored


def skill_gap(employee_skills, required_skill, required_level):
    """
    Returns None if the employee meets/exceeds the requirement, else a
    dict describing the gap. Matching is case-insensitive.
    """
    normalized = _normalize_skills(employee_skills)
    level = normalized.get(str(required_skill).strip().upper(), 0) if required_skill else 0
    if level >= required_level:
        return None
    return {
        "skill": required_skill,
        "required_level": required_level,
        "current_level": level,
        "gap": required_level - level,
    }


# ----------------------------------------------------------------------
# Step 3 additions: project-level team task allocation.
#
# These build ON TOP of employee_task_match_score() — same skill /
# workload / priority / urgency signals, same recommendation thresholds
# — rather than replacing it. employee_task_match_score() keeps being
# used unchanged everywhere it already is (single employee<->task
# lookups, recommend_task, etc). employee_task_allocation_score() below
# is only used by AIService.allocate_project_tasks() where a small
# role-affinity signal helps spread DIFFERENT tasks across a team
# (e.g. a "Frontend Developer" naturally leaning toward a JavaScript
# task over a "Backend Developer" doing the same lookup).
# ----------------------------------------------------------------------

ROLE_SKILL_HINTS = {
    "FRONTEND": ["HTML", "CSS", "JAVASCRIPT", "TYPESCRIPT", "REACT", "VUE", "ANGULAR", "UI"],
    "BACKEND": ["PYTHON", "FASTAPI", "FLASK", "DJANGO", "NODE", "JAVA", "SQL", "API", "DATABASE"],
    "UI": ["UI", "UX", "DESIGN", "FIGMA", "CSS", "PROTOTYPING"],
    "UX": ["UI", "UX", "DESIGN", "FIGMA", "PROTOTYPING"],
    "DESIGN": ["UI", "UX", "DESIGN", "FIGMA", "PROTOTYPING", "CSS"],
    "EMBEDDED": ["ESP32", "ARDUINO", "C", "C++", "FIRMWARE", "IOT", "RFID", "MICROCONTROLLER", "STM32"],
    "HARDWARE": ["ESP32", "ARDUINO", "C", "C++", "FIRMWARE", "IOT", "RFID", "MICROCONTROLLER", "STM32"],
    "FULLSTACK": ["HTML", "CSS", "JAVASCRIPT", "PYTHON", "SQL", "API", "REACT", "NODE"],
    "DATA": ["SQL", "PYTHON", "DATABASE", "ANALYTICS", "MACHINE LEARNING", "ML"],
}


def role_relevance_bonus(role, required_skill):
    """
    Small deterministic bonus (0-10) when an employee's job role
    naturally aligns with a task's required skill (e.g. role
    "Frontend Developer" + required_skill "JavaScript"). This is a
    secondary signal on top of skill_match_percentage, the primary
    driver — it never dominates the score. Returns 0 if role or
    required_skill is missing, or nothing recognized matches.
    """
    if not role or not required_skill:
        return 0.0
    role_up = str(role).strip().upper()
    skill_up = str(required_skill).strip().upper()
    for key, hints in ROLE_SKILL_HINTS.items():
        if key in role_up:
            if any(h in skill_up or skill_up in h for h in hints):
                return 10.0
    return 0.0


def employee_task_allocation_score(employee_skills, active_task_count, role, task, days_until_deadline=None):
    """
    Allocation-specific scoring used only by AIService.allocate_project_tasks().
    Same ingredients as employee_task_match_score() (skill match, workload/
    availability, priority, deadline urgency) plus role_relevance_bonus().

    A task with no required_skill set is treated as skill-neutral (60%)
    rather than an automatic zero, so generic/unlabeled tasks can still
    be allocated rather than always being skipped — this function is
    only used for whole-team allocation, so it needs to be able to
    place every kind of task, not just skill-tagged ones.

    Weights: skill match 40%, availability 25%, priority 15%,
    urgency 10%, plus role bonus (0-10) added on top.
    """
    required_skill = task.get("required_skill")
    if not required_skill:
        skill_pct = 60.0
        matched_level = None
    else:
        skill_pct = skill_match_percentage(
            employee_skills, required_skill, task.get("required_skill_level", 0)
        )
        normalized = _normalize_skills(employee_skills)
        matched_level = normalized.get(str(required_skill).strip().upper())

    workload_pct = workload_percentage(active_task_count)
    availability_score = round(100 - workload_pct, 1)
    prio_score = priority_score(task.get("priority"))
    urgency = deadline_urgency_score(days_until_deadline)
    role_bonus = role_relevance_bonus(role, required_skill)

    overall = round(
        skill_pct * 0.40 + availability_score * 0.25 + prio_score * 0.15 + urgency * 0.10 + role_bonus,
        1,
    )
    overall = min(overall, 100.0)

    if required_skill and skill_pct == 0:
        recommendation = "AVOID"
        reason = f"No matching skill on record for '{required_skill}'."
    elif overall >= 75:
        recommendation = "ASSIGN"
        bits = [f"skill match {skill_pct}%"]
        if role_bonus:
            bits.append("role aligns with task")
        bits.append(f"workload {workload_label(workload_pct)}")
        reason = "Strong fit — " + ", ".join(bits) + "."
    elif overall >= 45:
        recommendation = "CONSIDER"
        reason = f"Moderate fit — skill match {skill_pct}%, workload {workload_label(workload_pct)}."
    else:
        recommendation = "AVOID"
        reason = f"Weak fit — skill match {skill_pct}%, workload {workload_label(workload_pct)}."

    return {
        "skill_match_percent": skill_pct,
        "matched_skill_level": matched_level,
        "workload_percent": workload_pct,
        "workload_label": workload_label(workload_pct),
        "priority_score": prio_score,
        "urgency_score": urgency,
        "role_bonus": role_bonus,
        "overall_score": overall,
        "recommendation": recommendation,
        "reason": reason,
    }
