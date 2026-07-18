"""
Database Seeding Script for Smart Clinic System

This script populates the database with initial data including:
- Admin, Doctor, and Receptionist users
- Doctor profiles with specializations
- Working hours (Monday-Friday, 9 AM - 5 PM)
- Sample patients
- Sample appointments with reminder times

Usage:
    cd /path/to/backend
    source venv/bin/activate
    PYTHONPATH=/path/to/backend python3 scripts/seed.py

Note: PYTHONPATH is required for proper module imports.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.security import hash_password
from models.db_models import Appointment, Doctor, Patient, User, WorkingHours

def seed():
    db: Session = SessionLocal()

    # =========================
    # CLEAN DATABASE (optional but recommended)
    # =========================
    print("Cleaning database...")
    db.query(Appointment).delete()
    db.query(WorkingHours).delete()
    db.query(Doctor).delete()
    db.query(Patient).delete()
    db.query(User).delete()
    db.commit()

    # =========================
    # USERS
    # =========================
    print("Creating users...")

    admin = User(
        email="drmagdyfahmi9@gmail.com",
        password=hash_password("Magdy@1950"),
        role="admin",
        name="Admin User",
        is_active=True
    )

    doctor_user1 = User(
        email="dr.ahmed.hassan157@gmail.com",
        password=hash_password("Ahmed_doctor123"),
        role="doctor",
        name="Dr. Ahmed Hassan",
        is_active=True
    )

    doctor_user2 = User(
        email="dr.sara.ali153@gmail.com",
        password=hash_password("Sara_doctor123"),
        role="doctor",
        name="Dr. Sara Ali",
        is_active=True
    )
    
    doctor_user3 = User(
        email="dr.hamza.mahmoud12@gmail.com",
        password=hash_password("Hamza_doctor123"),
        role="doctor",
        name="Dr. Hamza Mahmoud",
        is_active=True
    )

    receptionist = User(
        email="mennaomardevops@gmail.com",
        password=hash_password("receptionist123"),
        role="receptionist",
        name="Receptionist User",
        is_active=True
    )

    db.add_all([admin, doctor_user1, doctor_user2, doctor_user3, receptionist])
    db.commit()

    # =========================
    # DOCTORS
    # =========================
    print("Creating doctors...")

    doctor1 = Doctor(
        user_id=doctor_user1.id,
        specialization="Cardiology"
    )

    doctor2 = Doctor(
        user_id=doctor_user2.id,
        specialization="Dermatology"
    )

    doctor3 = Doctor(
        user_id=doctor_user3.id,
        specialization="Internist"
    )

    db.add_all([doctor1, doctor2, doctor3])
    db.commit()

    # =========================
    # WORKING HOURS
    # =========================
    print("Creating working hours...")

    working_hours = []

    for doctor in [doctor1, doctor2, doctor3]:
        for day in range(0, 5):  # Monday → Friday
            working_hours.append(
                WorkingHours(
                    doctor_id=doctor.id,
                    day_of_week=day,
                    start_time="09:00",
                    end_time="17:00"
                )
            )

    db.add_all(working_hours)
    db.commit()

    # =========================
    # PATIENTS
    # =========================
    print("Creating patients...")

    patient1 = Patient(
        name="Ahmed Ali",
        phone="01000000001",
        email="ahmed@test.com"
    )

    patient2 = Patient(
        name="Sara Mohamed",
        phone="01000000002",
        email="sara@test.com"
    )

    db.add_all([patient1, patient2])
    db.commit()

    # =========================
    # APPOINTMENTS
    # =========================
    print("Creating appointments...")

    now = datetime.now()

    # Create appointments 2 days from now to ensure they're in the future
    appt1_start = now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=2)
    appt1 = Appointment(
        doctor_id=doctor1.id,
        patient_id=patient1.id,
        start_time=appt1_start,
        end_time=appt1_start + timedelta(minutes=30),
        status="SCHEDULED",
        reminder_time=appt1_start - timedelta(hours=1),  # 1 hour before
        reminder_sent=False
    )

    appt2_start = now.replace(hour=14, minute=30, second=0, microsecond=0) + timedelta(days=3)
    appt2 = Appointment(
        doctor_id=doctor2.id,
        patient_id=patient2.id,
        start_time=appt2_start,
        end_time=appt2_start + timedelta(minutes=30),
        status="SCHEDULED",
        reminder_time=appt2_start - timedelta(hours=1),  # 1 hour before
        reminder_sent=False
    )

    db.add_all([appt1, appt2])
    db.commit()

    print("SEED COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    # Run with: PYTHONPATH=/path/to/backend python3 scripts/seed.py
    seed()