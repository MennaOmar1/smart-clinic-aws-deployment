from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from core.database import get_db
from services.appointment_service import AppointmentService
from schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentStatusUpdate,
    AppointmentNotes,
    AppointmentResponse
)
from api.deps import require_roles
from models.db_models import Appointment, Doctor, WorkingHours
from schemas.doctor import DoctorProfileUpdate


router = APIRouter(tags=["Doctor"])


def get_doctor_id(user):
    return int(user.get("id") or user.get("sub"))


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):

    user_id = int(user.get("sub"))

    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user))
        .filter(Doctor.user_id == user_id)
        .first()
    )

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    working_hours = db.query(WorkingHours).filter(
        WorkingHours.doctor_id == doctor.id
    ).all()

    appointments_count = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).count()

    return {
        "id": doctor.id,

        "name": doctor.user.name,
        "email": doctor.user.email,

        "specialization": doctor.specialization,
        "bio": doctor.bio,
        "phone": doctor.phone,

        "google_connected": bool(doctor.google_token),

        "appointments_count": appointments_count,

        "working_hours": [
            {
                "day_of_week": w.day_of_week,
                "start_time": w.start_time,
                "end_time": w.end_time
            }
            for w in working_hours
        ]
    }


@router.patch("/profile")
def update_profile(
    data: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):

    user_id = int(user.get("sub"))

    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.user))
        .filter(Doctor.user_id == user_id)
        .first()
    )

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    if data.name is not None:
        doctor.user.name = data.name

    if data.specialization is not None:
        doctor.specialization = data.specialization

    if data.bio is not None:
        doctor.bio = data.bio

    if data.phone is not None:
        doctor.phone = data.phone

    if data.experience is not None:
        doctor.experience = data.experience

    if data.image_url is not None:
        doctor.image_url = data.image_url

    db.commit()
    db.refresh(doctor)

    return {
        "message": "Profile updated successfully"
    }
    

@router.post("/appointments", response_model=AppointmentResponse)
def create_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):

    user_id = int(user.get("sub"))

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user_id
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    import json

    credentials = None

    if doctor.google_token:
        try:
            credentials = json.loads(doctor.google_token)
        except:
            credentials = None

    try:

        return AppointmentService.book_appointment(
            db=db,
            doctor_id=doctor.id,
            start_time=data.time,
            patient_name=data.patient_name,
            patient_phone=data.patient_phone,
            patient_email=data.patient_email,
            notes=data.notes,
            credentials=credentials
        )

    except Exception as e:
        raise HTTPException(400, str(e))
    
    
@router.patch("/appointments/{appointment_id}/reschedule",response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: int,
    data: AppointmentReschedule,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):

    user_id = int(user.get("sub"))

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user_id
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    import json

    credentials = None

    if doctor.google_token:
        try:
            credentials = json.loads(doctor.google_token)
        except:
            credentials = None

    try:

        return AppointmentService.reschedule(
            db=db,
            appointment_id=appointment_id,
            new_time=data.time,
            credentials=credentials
        )

    except Exception as e:
        raise HTTPException(400, str(e))   

    
@router.patch("/appointments/{appointment_id}/cancel",response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):

    user_id = int(user.get("sub"))

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user_id
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    import json

    credentials = None

    if doctor.google_token:
        try:
            credentials = json.loads(doctor.google_token)
        except:
            credentials = None

    try:

        return AppointmentService.cancel(
            db=db,
            appointment_id=appointment_id,
            credentials=credentials
        )

    except Exception as e:
        raise HTTPException(400, str(e))
    


@router.get("/appointments", response_model=list[AppointmentResponse])
def get_my_appointments(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):
    user_id = int(user.get("sub"))

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user_id
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor).joinedload(Doctor.user),
            joinedload(Appointment.patient)
        )
        .filter(Appointment.doctor_id == doctor.id)
        .all()
    )

    return [
        AppointmentService.enrich_appointment(a)
        for a in appointments
    ]


@router.get("/appointments/{appointment_id}/status", response_model=AppointmentResponse)
def get_appointment_status(
    appointment_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):
    user_id = int(user.get("sub"))
    doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()

    if not doctor:
        raise HTTPException(404, "Doctor not found")

    appointment = AppointmentService.get_by_id(db, appointment_id)

    if not appointment or appointment.doctor_id != doctor.id:
        raise HTTPException(404, "Appointment not found")

    return appointment


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentResponse)
def update_status(
    appointment_id: int,
    data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):
    doctor_id = get_doctor_id(user)

    try:
        return AppointmentService.update_status(
            db,
            appointment_id,
            data.status
        )
    except Exception as e:
        raise HTTPException(400, str(e))


@router.patch("/appointments/{appointment_id}/notes", response_model=AppointmentResponse)
def add_notes(
    appointment_id: int,
    data: AppointmentNotes,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["doctor"]))
):
    doctor_id = get_doctor_id(user)

    try:
        return AppointmentService.add_notes(
            db,
            appointment_id,
            data.notes
        )
    except Exception as e:
        raise HTTPException(400, str(e))