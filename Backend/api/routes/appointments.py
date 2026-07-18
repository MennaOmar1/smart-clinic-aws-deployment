from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.db_models import Doctor
from services.appointment_service import AppointmentService
from schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentResponse
)
from api.deps import require_roles

router = APIRouter( tags=["Appointments"])


# =========================
# CREATE APPOINTMENT
# =========================
@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin", "receptionist"]))
):
    try:
        # 🔥 1. get doctor
        doctor = db.query(Doctor).filter(Doctor.id == data.doctor_id).first()

        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        # 🔥 2. parse google token
        credentials = None

        if doctor.google_token:
            import json
            try:
                print("DOCTOR ID:", doctor.id)
                print("DOCTOR OBJECT:", doctor)
                print("GOOGLE TOKEN FIELD:", repr(doctor.google_token))
                credentials = json.loads(doctor.google_token)
            except:
                credentials = None
        print("DOCTOR TOKEN RAW:", doctor.google_token)
        # 🔥 3. call service WITH credentials
        return AppointmentService.book_appointment(
            db=db,
            doctor_id=data.doctor_id,
            start_time=data.time,
            patient_name=data.patient_name,
            patient_phone=data.patient_phone,
            patient_email=data.patient_email,
            notes=data.notes,
            credentials=credentials   # ✔️ NOW IT WORKS
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================
# CANCEL
# =========================
@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin", "receptionist"]))
):
    try:
        return AppointmentService.cancel(db, appointment_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# =========================
# RESCHEDULE
# =========================
@router.patch("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin", "receptionist"]))
):
    try:
        return AppointmentService.reschedule(
            db,
            appointment_id,
            data.time
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================
# GET ALL
# =========================
@router.get("/", response_model=list[AppointmentResponse])
def get_all(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin", "receptionist"]))
):
    return AppointmentService.get_all(db)


# =========================
# GET ONE
# =========================
@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_one(
    appointment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["admin", "receptionist"]))
):
    appt = AppointmentService.get_by_id(db, appointment_id)

    if not appt:
        raise HTTPException(status_code=404, detail="Not found")

    return appt


# =========================
# AVAILABLE SLOTS
# =========================
@router.get("/doctors/{doctor_id}/available-slots")
def available_slots(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    slots = AppointmentService.generate_slots(
        db,
        doctor_id,
        datetime.now()
    )

    return {
        "slots": [s.isoformat() for s in slots]
    }