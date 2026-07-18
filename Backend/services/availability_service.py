from datetime import datetime
from services.appointment_service import AppointmentService


class AvailabilityService:

    @staticmethod
    def get_available_slots(db, doctor_id, date: datetime):
        slots = AppointmentService.generate_slots(db, doctor_id, date)
        return [s.isoformat() for s in slots]