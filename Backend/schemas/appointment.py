from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# ================================
# CREATE APPOINTMENT
# ================================
class AppointmentCreate(BaseModel):
    doctor_id: int = Field(..., gt=0)
    patient_name: str = Field(..., min_length=2)
    patient_phone: str = Field(..., min_length=6)
    patient_email: Optional[EmailStr] = None
    time: datetime
    notes: Optional[str] = None


# ================================
# RESCHEDULE
# ================================
class AppointmentReschedule(BaseModel):
    time: datetime


# ================================
# STATUS UPDATE (Doctor)
# ================================
class AppointmentStatusUpdate(BaseModel):
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "status": "COMPLETED"
            }
        }


# ================================
# ADD NOTES
# ================================
class AppointmentNotes(BaseModel):
    notes: str = Field(..., min_length=1)


# ================================
# ADMIN UPDATE
# ================================
class AdminUpdateAppointment(BaseModel):
    time: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


# ================================
# RESPONSE MODEL (IMPORTANT)
# ================================
class AppointmentResponse(BaseModel):

    id: int

    doctor_id: int
    doctor_name: str | None = None
    doctor_email: str | None = None

    patient_id: int
    patient_name: str | None = None
    patient_phone: str | None = None
    patient_email: str | None = None

    start_time: datetime
    end_time: datetime

    status: str
    notes: str | None = None

    google_event_id: str | None = None

    reminder_time: datetime | None = None
    reminder_sent: bool | None = None

    class Config:
        from_attributes = True