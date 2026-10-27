"""
Additive migration for WorkforceX task-management upgrade.

Safe to run multiple times: every ALTER TABLE is wrapped so an
"already exists" error is ignored. Does NOT drop or rename any
existing column, table, or row. Run from the database/ folder:

    cd database
    python migrate_task_management.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workforce.db")


def add_column(cursor, table, coldef):
    col_name = coldef.split()[0]
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {coldef}")
        print(f"  + {table}.{col_name} added")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print(f"  = {table}.{col_name} already exists, skipping")
        else:
            raise


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("tasks:")
    # progress/status/completed_at were already declared in the SQLAlchemy
    # model but never actually migrated into the live sqlite file, so we
    # add them here alongside the genuinely new columns.
    add_column(cur, "tasks", "progress INTEGER DEFAULT 0")
    add_column(cur, "tasks", "completed_at TEXT")
    add_column(cur, "tasks", "assigned_date TEXT")
    add_column(cur, "tasks", "start_date TEXT")
    add_column(cur, "tasks", "assigned_by TEXT")
    add_column(cur, "tasks", "completion_notes TEXT")
    add_column(cur, "tasks", "created_at TEXT")
    add_column(cur, "tasks", "updated_at TEXT")

    print("projects:")
    add_column(cur, "projects", "created_at TEXT")
    add_column(cur, "projects", "updated_at TEXT")
    add_column(cur, "projects", "start_date TEXT")
    # NOTE: no stored progress_percentage column on projects by design —
    # progress is computed on the fly from task progress (see
    # backend/project_progress.py) so it can never drift or be hardcoded.

    print("task_history (audit trail):")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            employee_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            old_progress INTEGER,
            new_progress INTEGER,
            changed_by TEXT,
            notes TEXT,
            changed_at TEXT NOT NULL
        )
    """)
    print("  + task_history table ready")

    conn.commit()
    conn.close()
    print("\nMigration complete. No existing data was modified or deleted.")


if __name__ == "__main__":
    main()
