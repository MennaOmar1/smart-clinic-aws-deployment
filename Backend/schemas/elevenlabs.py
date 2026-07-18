from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ElevenLabsAvailabilityResponse(BaseModel):
    is_available: bool
    availability_message: str


class ElevenLabsBookingRequest(BaseModel):
    doctor_id: int = Field(..., gt=0)
    patient_name: str = Field(..., min_length=2)
    patient_phone: str = Field(..., min_length=6)
    time: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None
    patient_email: Optional[EmailStr] = None


class ElevenLabsBookingResponse(BaseModel):
    booking_success: bool
    booking_confirmation: str
    appointment_id: Optional[int] = None


class ElevenLabsDoctor(BaseModel):
    id: int
    name: Optional[str] = None
    specialty: Optional[str] = None


class ElevenLabsDoctorsResponse(BaseModel):
    doctors: list[ElevenLabsDoctor]
