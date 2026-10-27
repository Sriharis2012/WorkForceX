import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))
from database import SessionLocal, Employee

db = SessionLocal()
priya = db.query(Employee).filter(Employee.name == "Priya").first()
priya.availability = "Busy"
priya.workload = 70
db.commit()
db.close()
print("Priya's status updated!")