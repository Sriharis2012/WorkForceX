from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "workforce.db")
DB_PATH = os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH)

# On first deployment to a persistent disk, copy the bundled demo database
# only if the persistent database does not exist yet.
if DB_PATH != DEFAULT_DB_PATH and not os.path.exists(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DEFAULT_DB_PATH):
        import shutil
        shutil.copy2(DEFAULT_DB_PATH, DB_PATH)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    employee_id = Column(String, unique=True)
    rfid_uid = Column(String, unique=True)
    name = Column(String)
    department = Column(String)
    role = Column(String)
    availability = Column(String, default="Available")
    workload = Column(Float, default=0)
    performance_score = Column(Float, default=0)
    current_project_id = Column(Integer, nullable=True)
    current_project_name = Column(String, nullable=True)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    skill_name = Column(String, unique=True)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    project_name = Column(String)
    description = Column(String)
    priority = Column(String)
    deadline = Column(String)
    status = Column(String, default="Not Started")
    start_date = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)
    # No stored progress_percentage: project progress is always computed
    # from its tasks (see backend/project_progress.py), never hardcoded.


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer)
    task_name = Column(String)
    description = Column(String)
    required_skill = Column(String)
    required_skill_level = Column(Integer)
    priority = Column(String)
    deadline = Column(String)
    assigned_employee_id = Column(Integer)

    progress = Column(Integer, default=0)
    status = Column(String, default="PENDING")
    completed_at = Column(String, nullable=True)

    # Task-management fields
    assigned_date = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    assigned_by = Column(String, nullable=True)
    completion_notes = Column(String, nullable=True)
    # Step 4: optional evidence/result reference for a SUBMITTED task
    # (a URL, GitHub link, file path, etc). Never required — a worker
    # can submit with only completion_notes describing the result.
    evidence_url = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


class TaskHistory(Base):
    """Audit trail: one row per status/progress change on a task.
    Completed tasks and their history are never deleted."""
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    employee_id = Column(Integer, nullable=True)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    old_progress = Column(Integer, nullable=True)
    new_progress = Column(Integer, nullable=True)
    changed_by = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    changed_at = Column(String, nullable=False)


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer)
    skill_name = Column(String)
    skill_level = Column(Integer)


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    employee_id = Column(Integer)
    employee_name = Column(String)
    skill_match_score = Column(Float)
    status = Column(String, default="Approved")


class ProjectMember(Base):
    """
    Authoritative project<->employee relationship (Step 3 fix).
    AI team allocation reads project teams from here — NOT from
    Employee.current_project_id/current_project_name, which remain on
    the Employee model purely for backward compatibility with the
    existing dashboard/RFID display.
    """
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    employee_id = Column(Integer, nullable=False)
    project_role = Column(String, nullable=True)
    joined_at = Column(String, nullable=True)
    status = Column(String, default="ACTIVE")  # ACTIVE or REMOVED — rows are never deleted


Base.metadata.create_all(bind=engine)


def _ensure_column(table_name, column_name, column_ddl):
    """
    Lightweight, additive sqlite migration: create_all() only creates
    MISSING TABLES, it never adds a missing column to a table that
    already exists on disk. Without this, a workforce.db created
    before Step 4 would be missing Task.evidence_url and every query
    would break. Safe to call every startup — it's a no-op once the
    column exists, and it never touches existing data.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        existing_cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})"))}
        if column_name not in existing_cols:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}"))
            conn.commit()


_ensure_column("tasks", "evidence_url", "VARCHAR")

print("Database created successfully!")