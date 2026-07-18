from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.orm import Session

from core.database import get_db
from core.elevenlabs_config import ELEVENLABS_SLOT_MINUTES, ELEVENLABS_TIMEZONE
from models.db_models import Doctor
from schemas.elevenlabs import (
    ElevenLabsAvailabilityResponse,
    ElevenLabsBookingRequest,
    ElevenLabsBookingResponse,
    ElevenLabsDoctorsResponse,
)
from services.elevenlabs_scheduling_service import (
    ElevenLabsSchedulingError,
    ElevenLabsSchedulingService,
)


router = APIRouter(
    prefix="/elevenlabs",
    tags=["ElevenLabs"],
)

datetime_adapter = TypeAdapter(datetime)


@router.get("/availability", response_model=ElevenLabsAvailabilityResponse)
def check_availability(
    doctor_id: str | None = Query(None),
    requested_time: str | None = Query(None, alias="time"),
    db: Session = Depends(get_db),
):
    parsed_doctor_id = _parse_positive_int(doctor_id)
    parsed_time = _parse_datetime(requested_time)
    if parsed_doctor_id is None or parsed_time is None:
        return _availability_validation_error(
            doctor_id=parsed_doctor_id,
            requested_time=requested_time,
        )

    try:
        return ElevenLabsSchedulingService.check_availability(
            db,
            doctor_id=parsed_doctor_id,
            requested_time=parsed_time,
        )
    except SQLAlchemyTimeoutError:
        return JSONResponse(
            status_code=504,
            content={
                "is_available": False,
                "availability_message": "Scheduling service timed out",
                "doctor_id": parsed_doctor_id,
                "requested_time": parsed_time.isoformat(timespec="seconds"),
                "normalized_time": None,
                "timezone": ELEVENLABS_TIMEZONE,
                "slot_minutes": ELEVENLABS_SLOT_MINUTES,
                "error_code": "SCHEDULING_TIMEOUT",
                "message": "Scheduling service timed out",
            },
        )


@router.post("/book", response_model=ElevenLabsBookingResponse)
def book_appointment(
    payload: object = Body(None),
    db: Session = Depends(get_db),
):
    try:
        booking = ElevenLabsBookingRequest.model_validate(payload)
    except ValidationError:
        doctor_id = payload.get("doctor_id") if isinstance(payload, dict) else None
        return _booking_validation_error(doctor_id=doctor_id)

    notes = booking.notes if booking.notes is not None else booking.reason
    try:
        return ElevenLabsSchedulingService.book_appointment(
            db,
            doctor_id=booking.doctor_id,
            requested_time=booking.time,
            patient_name=booking.patient_name,
            patient_phone=booking.patient_phone,
            patient_email=booking.patient_email,
            notes=notes,
        )
    except ElevenLabsSchedulingError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)
    except SQLAlchemyTimeoutError:
        return JSONResponse(
            status_code=504,
            content={
                "booking_success": False,
                "booking_confirmation": "Scheduling service timed out",
                "appointment_id": None,
                "doctor_id": booking.doctor_id,
                "start_time": None,
                "end_time": None,
                "timezone": ELEVENLABS_TIMEZONE,
                "status": None,
                "error_code": "SCHEDULING_TIMEOUT",
                "message": "Scheduling service timed out",
            },
        )


@router.get("/doctors", response_model=ElevenLabsDoctorsResponse)
def list_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).all()
    return {
        "doctors": [
            {
                "id": doctor.id,
                "name": doctor.user.name if doctor.user else None,
                "specialty": doctor.specialization,
            }
            for doctor in doctors
        ],
        "message": "Doctors loaded",
    }


def _parse_positive_int(value: str | None) -> int | None:
    try:
        parsed = int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime_adapter.validate_python(value)
    except ValidationError:
        return None


def _availability_validation_error(
    doctor_id: int | None,
    requested_time: str | None,
) -> JSONResponse:
    message = "Invalid doctor_id or time. Use a positive doctor_id and ISO 8601 time."
    return JSONResponse(
        status_code=422,
        content={
            "is_available": False,
            "availability_message": message,
            "doctor_id": doctor_id,
            "requested_time": requested_time,
            "normalized_time": None,
            "timezone": ELEVENLABS_TIMEZONE,
            "slot_minutes": ELEVENLABS_SLOT_MINUTES,
            "error_code": "VALIDATION_ERROR",
            "message": message,
        },
    )


def _booking_validation_error(doctor_id: object = None) -> JSONResponse:
    message = "Invalid booking payload. Provide doctor_id, patient_name, patient_phone, and ISO 8601 time."
    safe_doctor_id = doctor_id if isinstance(doctor_id, int) else None
    return JSONResponse(
        status_code=422,
        content={
            "booking_success": False,
            "booking_confirmation": message,
            "appointment_id": None,
            "doctor_id": safe_doctor_id,
            "start_time": None,
            "end_time": None,
            "timezone": ELEVENLABS_TIMEZONE,
            "status": None,
            "error_code": "VALIDATION_ERROR",
            "message": message,
        },
    )
