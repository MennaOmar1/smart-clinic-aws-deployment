from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import hash_password
from models.db_models import User, Doctor, Appointment
from schemas.user import UserCreate, UserResponse
from services.appointment_service import AppointmentService
from schemas.appointment import (
    AdminUpdateAppointment,
    AppointmentResponse
)
from api.deps import require_roles
from datetime import timedelta
from services.calendar_sync_service import CalendarSyncService
from services.email_service import send_email

import json

router = APIRouter(tags=["Admin"])


# ================= GET ALL APPOINTMENTS =================
@router.get(
    "/appointments",
    response_model=list[AppointmentResponse]
)
def get_all_appointments(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):
    return AppointmentService.get_all(db)


# ================= FILTER APPOINTMENTS =================
@router.get("/appointments/filter")
def filter_appointments(
    doctor_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):

    appointments = AppointmentService.get_all(db)

    if doctor_id:
        appointments = [
            a for a in appointments
            if a["doctor_id"] == doctor_id
        ]

    if status:
        appointments = [
            a for a in appointments
            if a["status"] == status
        ]

    return {"appointments": appointments}


# ================= UPDATE APPOINTMENT =================
@router.patch(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse
)
def update_appointment(
    appointment_id: int,
    data: AdminUpdateAppointment,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):

    # REAL ORM OBJECT
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appt:
        raise HTTPException(404, "Appointment not found")

    # ================= GOOGLE TOKEN =================
    doctor = db.query(Doctor).filter(
        Doctor.id == appt.doctor_id
    ).first()

    google_token = None

    if doctor and doctor.google_token:
        google_token = json.loads(doctor.google_token)

    # ================= UPDATE STATUS =================
    if data.status:
        appt.status = data.status

    # ================= UPDATE NOTES =================
    if data.notes:
        appt.notes = data.notes

    # ================= RESCHEDULE =================
    if data.time:

        if not AppointmentService.is_available(
            db,
            appt.doctor_id,
            data.time
        ):
            raise HTTPException(
                status_code=400,
                detail="Time slot not available"
            )

        appt.start_time = data.time
        appt.end_time = data.time + timedelta(minutes=30)

        # Google Calendar update
        CalendarSyncService.update(
            db=db,
            appointment_id=appt.id,
            new_time=data.time,
            google_token=google_token
        )

    db.commit()
    db.refresh(appt)

    return AppointmentService.enrich_appointment(appt)


# ================= DELETE APPOINTMENT =================
@router.delete("/appointments/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):

    # REAL ORM OBJECT
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id
    ).first()

    if not appt:
        raise HTTPException(404, "Appointment not found")

    # ================= GOOGLE TOKEN =================
    doctor = db.query(Doctor).filter(
        Doctor.id == appt.doctor_id
    ).first()

    google_token = None

    if doctor and doctor.google_token:
        google_token = json.loads(doctor.google_token)

    # ================= GOOGLE DELETE =================
    CalendarSyncService.delete(
        db=db,
        appointment_id=appt.id,
        google_token=google_token
    )

    db.delete(appt)
    db.commit()

    return {"message": "Deleted successfully"}


# ================= CREATE USER =================
@router.post("/users", response_model=UserResponse)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):

    existing = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing:
        raise HTTPException(400, "User already exists")

    new_user = User(
        email=data.email,
        role=data.role,
        name=data.email.split("@")[0],
        password=hash_password("123456")
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ================= GET USERS =================
@router.get("/users", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):
    return db.query(User).all()


# ================= DELETE USER =================
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin"]))
):

    u = db.query(User).filter(
        User.id == user_id
    ).first()

    if not u:
        raise HTTPException(404, "User not found")

    db.delete(u)
    db.commit()

    return {"message": "User deleted"}






# ================= TEST EMAIL =================
@router.post("/test-email")
def test_email():

    send_email(
        to_email="omarmenna041@gmail.com",
        subject="Test Email",
        body="Hello 👋 this is a test from FastAPI"
    )

    return {"message": "Email sent (check inbox)"}