"""
Auto-seed script that runs on startup.
Only seeds when the doctors table is empty — safe to call on every deploy.
"""

from core.database import SessionLocal
from core.security import hash_password
from models.db_models import Doctor, Patient, User, WorkingHours


def auto_seed_if_empty():
    """Seed essential data only if the doctors table is empty."""
    db = SessionLocal()
    try:
        existing_doctors = db.query(Doctor).count()
        if existing_doctors > 0:
            print(f"✅ Auto-seed skipped — {existing_doctors} doctor(s) already exist")
            return

        print("🌱 Auto-seeding database (doctors table is empty)...")

        # =========================
        # USERS
        # =========================
        admin = User(
            email="drmagdyfahmi9@gmail.com",
            password=hash_password("admin123"),
            role="admin",
            name="Admin User",
            is_active=True,
        )

        doctor_user1 = User(
            email="mennaeb743@gmail.com",
            password=hash_password("doctor1"),
            role="doctor",
            name="Dr. Ahmed Hassan",
            is_active=True,
        )

        doctor_user2 = User(
            email="omarmenna041@gmail.com",
            password=hash_password("doctor2"),
            role="doctor",
            name="Dr. Sara Ali",
            is_active=True,
        )

        doctor_user3 = User(
            email="dr.khalid.mahmoud@gmail.com",
            password=hash_password("doctor3"),
            role="doctor",
            name="Dr. Khalid Mahmoud",
            is_active=True,
        )

        receptionist = User(
            email="mennaomardevops@gmail.com",
            password=hash_password("receptionist123"),
            role="receptionist",
            name="Receptionist User",
            is_active=True,
        )

        db.add_all([admin, doctor_user1, doctor_user2, doctor_user3, receptionist])
        db.commit()

        # =========================
        # DOCTORS
        # =========================
        doctor1 = Doctor(user_id=doctor_user1.id, specialization="Cardiology")
        doctor2 = Doctor(user_id=doctor_user2.id, specialization="Dermatology")
        doctor3 = Doctor(user_id=doctor_user3.id, specialization="Internist")

        db.add_all([doctor1, doctor2, doctor3])
        db.commit()

        # =========================
        # WORKING HOURS (Mon-Fri, 08:00-17:00)
        # =========================
        for doc in [doctor1, doctor2, doctor3]:
            for day in range(0, 5):
                db.add(
                    WorkingHours(
                        doctor_id=doc.id,
                        day_of_week=day,
                        start_time="08:00",
                        end_time="17:00",
                    )
                )
        db.commit()

        # =========================
        # SAMPLE PATIENTS
        # =========================
        db.add_all([
            Patient(name="Ahmed Ali", phone="01000000001", email="ahmed@test.com"),
            Patient(name="Sara Mohamed", phone="01000000002", email="sara@test.com"),
        ])
        db.commit()

        print("✅ Auto-seed completed — 3 doctors, 5 users, 2 patients created")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Auto-seed error (non-fatal): {e}")
    finally:
        db.close()
