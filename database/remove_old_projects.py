from database import SessionLocal, Project

db = SessionLocal()
projects = db.query(Project).all()
for p in projects:
    db.delete(p)
db.commit()
db.close()
print("All old projects removed!")