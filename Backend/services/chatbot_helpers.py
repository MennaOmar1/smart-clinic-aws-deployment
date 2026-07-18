import uuid
import uuid
from models.db_models import Doctor, Patient, Appointment
from services.appointment_service import AppointmentService
from datetime import datetime, timedelta
from services.calendar_sync_service import CalendarSyncService

def get_doctors_by_specialization(db, specialization):
    return db.query(Doctor).filter(
        Doctor.specialization == specialization
    ).all()



def create_booking(db, data):

    doctor_id = data.get("doctor_id")
    start_time = data.get("start_time")
    patient_name = data.get("patient_name", "Chat User")
    patient_email = data.get("patient_email")
    patient_phone = data.get("patient_phone")
    google_token = data.get("google_token")  # 🔥 مهم

    if not doctor_id or not start_time:
        raise ValueError("Missing booking data")

    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)

    if not patient_phone:
        patient_phone = f"chat-{uuid.uuid4()}"

    # 1️⃣ create appointment in DB
    appointment = AppointmentService.book_appointment(
        db=db,
        doctor_id=doctor_id,
        start_time=start_time,
        patient_name=patient_name,
        patient_phone=patient_phone,
        patient_email=patient_email,
        notes=data.get("notes")
    )

    # 2️⃣ sync with Google Calendar
    if google_token:
        event_id = CalendarSyncService.create(appointment, google_token)

        appointment.google_event_id = event_id
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

    return appointment



def set_doctor(session, doctor_id):
    session["booking"]["doctor_id"] = doctor_id
    return session


def set_date(session, date):
    session["booking"]["date"] = date
    return session


def set_slot(session, slot):
    session["booking"]["slot"] = slot
    return session