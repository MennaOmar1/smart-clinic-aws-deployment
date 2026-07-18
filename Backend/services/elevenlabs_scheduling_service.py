from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from core.elevenlabs_config import (
    ELEVENLABS_SLOT_MINUTES,
    ELEVENLABS_TIMEZONE,
)
from models.db_models import Appointment, Doctor, Patient
from services.calendar_sync_service import CalendarSyncService


CAIRO_TZ = ZoneInfo(ELEVENLABS_TIMEZONE)
WORK_START = time(8, 0)
WORK_END = time(17, 0)


class ElevenLabsSchedulingError(Exception):
    def __init__(self, status_code: int, payload: dict):
        super().__init__(payload.get("message", "Scheduling error"))
        self.status_code = status_code
        self.payload = payload


class ElevenLabsSchedulingService:
    @staticmethod
    def normalize_to_cairo(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=CAIRO_TZ)
        return value.astimezone(CAIRO_TZ)

    @staticmethod
    def check_availability(
        db: Session,
        doctor_id: int,
        requested_time: datetime,
        now: datetime | None = None,
    ) -> dict:
        normalized = ElevenLabsSchedulingService.normalize_to_cairo(requested_time)
        now_cairo = ElevenLabsSchedulingService.normalize_to_cairo(now or datetime.now(CAIRO_TZ))

        base = {
            "is_available": False,
            "availability_message": "",
            "doctor_id": doctor_id,
            "requested_time": requested_time.isoformat(timespec="seconds"),
            "normalized_time": normalized.isoformat(timespec="seconds"),
            "timezone": ELEVENLABS_TIMEZONE,
            "slot_minutes": ELEVENLABS_SLOT_MINUTES,
            "error_code": None,
            "message": "",
        }

        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            return ElevenLabsSchedulingService._availability_error(
                base,
                "DOCTOR_NOT_FOUND",
                "Doctor was not found",
            )

        validation_error = ElevenLabsSchedulingService._validate_slot(normalized, now_cairo)
        if validation_error:
            error_code, message = validation_error
            return ElevenLabsSchedulingService._availability_error(base, error_code, message)

        if ElevenLabsSchedulingService._slot_exists(db, doctor_id, normalized):
            return ElevenLabsSchedulingService._availability_error(
                base,
                "SLOT_CONFLICT",
                "Requested slot is already booked",
            )

        base["is_available"] = True
        base["availability_message"] = "Slot is available"
        base["message"] = "Slot is available"
        return base

    @staticmethod
    def book_appointment(
        db: Session,
        doctor_id: int,
        requested_time: datetime,
        patient_name: str,
        patient_phone: str,
        patient_email: str | None = None,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> dict:
        availability = ElevenLabsSchedulingService.check_availability(
            db,
            doctor_id=doctor_id,
            requested_time=requested_time,
            now=now,
        )
        if not availability["is_available"]:
            raise ElevenLabsSchedulingError(
                ElevenLabsSchedulingService._status_for_error(availability["error_code"]),
                ElevenLabsSchedulingService._booking_error_payload(availability),
            )

        start_time = ElevenLabsSchedulingService.normalize_to_cairo(requested_time)
        end_time = start_time + timedelta(minutes=ELEVENLABS_SLOT_MINUTES)
        patient = ElevenLabsSchedulingService._get_or_create_patient(
            db,
            patient_name,
            patient_phone,
            patient_email,
        )

        appointment = Appointment(
            doctor_id=doctor_id,
            patient_id=patient.id,
            start_time=ElevenLabsSchedulingService._to_db_time(start_time),
            end_time=ElevenLabsSchedulingService._to_db_time(end_time),
            status="SCHEDULED",
            notes=notes,
            reminder_time=ElevenLabsSchedulingService._to_db_time(start_time - timedelta(hours=1)),
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        # Google sync
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            if doctor.google_token:
                import json
                try:
                    google_creds = json.loads(doctor.google_token)
                    google_event_id = CalendarSyncService.create(
                        db=db,
                        appointment_id=appointment.id,
                        google_token=google_creds)
                    if google_event_id:
                        appointment.google_event_id = google_event_id
                except Exception as e:
                    appointment.notes = (appointment.notes or "") + f"\n[Sync Config Error: {str(e)}]"
            else:
                appointment.notes = (appointment.notes or "") + "\n[Google Sync Skipped: Doctor has no Google Token saved in the system]"
            
            db.commit()

        confirmation = (
            f"Appointment confirmed for {start_time.strftime('%Y-%m-%d %H:%M')} "
            f"{ELEVENLABS_TIMEZONE}"
        )
        return {
            "booking_success": True,
            "booking_confirmation": confirmation,
            "appointment_id": appointment.id,
            "doctor_id": doctor_id,
            "start_time": start_time.isoformat(timespec="seconds"),
            "end_time": end_time.isoformat(timespec="seconds"),
            "timezone": ELEVENLABS_TIMEZONE,
            "status": appointment.status,
            "error_code": None,
            "message": confirmation,
        }

    @staticmethod
    def _availability_error(base: dict, error_code: str, message: str) -> dict:
        base["availability_message"] = message
        base["error_code"] = error_code
        base["message"] = message
        return base

    @staticmethod
    def _validate_slot(start_time: datetime, now: datetime) -> tuple[str, str] | None:
        if start_time <= now:
            return "PAST_TIME", "Appointments must be scheduled in the future"

        if start_time.weekday() > 4:
            return "OUTSIDE_WORKING_DAYS", "Appointments are available Monday to Friday only"

        slot_time = start_time.timetz().replace(tzinfo=None)
        end_time = (start_time + timedelta(minutes=ELEVENLABS_SLOT_MINUTES)).timetz().replace(tzinfo=None)
        if slot_time < WORK_START or end_time > WORK_END:
            return "OUTSIDE_WORKING_HOURS", "Appointments are available from 08:00 to 17:00 Africa/Cairo"

        if start_time.minute % ELEVENLABS_SLOT_MINUTES != 0 or start_time.second or start_time.microsecond:
            return "INVALID_SLOT_ALIGNMENT", "Appointments must start on a 30-minute boundary"

        return None

    @staticmethod
    def _slot_exists(db: Session, doctor_id: int, start_time: datetime) -> bool:
        existing = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time == ElevenLabsSchedulingService._to_db_time(start_time),
            Appointment.status != "CANCELLED",
        ).first()
        return existing is not None

    @staticmethod
    def _get_or_create_patient(
        db: Session,
        name: str,
        phone: str,
        email: str | None,
    ) -> Patient:
        patient = db.query(Patient).filter(Patient.phone == phone).first()
        if patient:
            if email and not patient.email:
                patient.email = email
                db.commit()
                db.refresh(patient)
            return patient

        patient = Patient(name=name, phone=phone, email=email)
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient

    @staticmethod
    def _to_db_time(value: datetime) -> datetime:
        return ElevenLabsSchedulingService.normalize_to_cairo(value).replace(
            tzinfo=None, second=0, microsecond=0
        )

    @staticmethod
    def _status_for_error(error_code: str | None) -> int:
        if error_code == "SLOT_CONFLICT":
            return 409
        if error_code == "DOCTOR_NOT_FOUND":
            return 404
        return 422

    @staticmethod
    def _booking_error_payload(availability: dict) -> dict:
        message = availability["message"]
        return {
            "booking_success": False,
            "booking_confirmation": message,
            "appointment_id": None,
            "doctor_id": availability.get("doctor_id"),
            "start_time": availability.get("normalized_time"),
            "end_time": None,
            "timezone": ELEVENLABS_TIMEZONE,
            "status": None,
            "error_code": availability.get("error_code"),
            "message": message,
        }
