from datetime import datetime, timedelta

from core.database import SessionLocal
from models.db_models import Appointment
from services.email_service import send_email


def send_reminder(appointment):

    send_email(
        to_email=appointment.patient.email,
        subject="Appointment Reminder",
        body=f"""
Hello {appointment.patient.name},

This is a reminder for your appointment.

Doctor: Dr. {appointment.doctor.user.name}
Time: {appointment.start_time}

Thank you,
Clinify Support
"""
    )

    print(f"Reminder sent to {appointment.patient.email}")


def run_reminders():

    db = SessionLocal()

    try:

        now = datetime.now()

        upcoming = now + timedelta(hours=1)

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.reminder_sent == False,
                Appointment.status == "SCHEDULED",
                Appointment.start_time <= upcoming,
                Appointment.start_time > now
            )
            .all()
        )

        for appointment in appointments:

            send_reminder(appointment)

            appointment.reminder_sent = True

        db.commit()

    finally:
        db.close()