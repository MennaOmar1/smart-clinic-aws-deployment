from zoneinfo import ZoneInfo
import logging

import json
from sqlalchemy.orm import joinedload

from core.google_calendar import (
    get_calendar_service,
    create_event,
    update_event,
    delete_event
)

from models.db_models import Appointment, Doctor


logger = logging.getLogger(__name__)

CAIRO_TZ = ZoneInfo("Africa/Cairo")


class CalendarSyncService:

    @staticmethod
    def create(db, appointment_id, google_token):

        if not google_token:
            logger.error("Google token is missing")
            return None

        try:

            # Reload appointment with relationships
            appointment = (
                db.query(Appointment)
                .options(
                    joinedload(Appointment.doctor).joinedload(Doctor.user),
                    joinedload(Appointment.patient)
                )
                .filter(Appointment.id == appointment_id)
                .first()
            )

            if not appointment:
                logger.error(f"Appointment {appointment_id} not found")
                return None

            if not appointment.doctor:
                logger.error("Appointment doctor is missing")
                return None

            if not appointment.patient:
                logger.error("Appointment patient is missing")
                return None
            
            print("GOOGLE TOKEN FROM DB:")
            print(json.dumps(google_token, indent=2))
            
            service = get_calendar_service(google_token)

            doctor_name = (
                appointment.doctor.user.name
                if appointment.doctor.user
                else "Unknown Doctor"
            )

            patient_name = appointment.patient.name or "Unknown Patient"

            # Add timezone explicitly
            start = appointment.start_time.replace(tzinfo=CAIRO_TZ)
            end = appointment.end_time.replace(tzinfo=CAIRO_TZ)

            logger.info(f"Creating Google Calendar event")
            logger.info(f"Doctor: {doctor_name}")
            logger.info(f"Patient: {patient_name}")
            logger.info(f"Start: {start.isoformat()}")
            logger.info(f"End: {end.isoformat()}")

            event_id = create_event(
                service=service,
                summary=f"Appointment - Dr {doctor_name} with {patient_name}",
                start_time=start.isoformat(),
                end_time=end.isoformat(),
                description=f"""
Patient: {patient_name}
Doctor: {doctor_name}
Status: {appointment.status}
""",
                attendee_email=appointment.patient.email
            )

            logger.info(f"Google Calendar event created: {event_id}")

            return event_id

        except Exception as e:

            logger.exception("Google Calendar create failed")

            try:
                appointment.notes = (
                    (appointment.notes or "")
                    + f"\n[Google Sync Failed: {str(e)}]"
                )

                db.commit()

            except Exception:
                logger.exception("Failed to save sync error notes")

            return None

    @staticmethod
    def update(db, appointment_id, new_time, google_token):

        if not google_token:
            logger.error("Google token missing")
            return

        try:

            appointment = (
                db.query(Appointment)
                .filter(Appointment.id == appointment_id)
                .first()
            )

            if not appointment:
                logger.error(f"Appointment {appointment_id} not found")
                return

            if not appointment.google_event_id:
                logger.error("No Google event id found")
                return

            service = get_calendar_service(google_token)

            start = new_time.replace(tzinfo=CAIRO_TZ)

            logger.info(
                f"Updating Google event {appointment.google_event_id}"
            )

            update_event(
                service,
                appointment.google_event_id,
                start.isoformat()
            )

        except Exception as e:
            logger.exception("Google update failed")

    @staticmethod
    def delete(db, appointment_id, google_token):

        if not google_token:
            logger.error("Google token missing")
            return

        try:

            appointment = (
                db.query(Appointment)
                .filter(Appointment.id == appointment_id)
                .first()
            )

            if not appointment:
                logger.error(f"Appointment {appointment_id} not found")
                return

            if not appointment.google_event_id:
                logger.error("No Google event id found")
                return

            service = get_calendar_service(google_token)

            logger.info(
                f"Deleting Google event {appointment.google_event_id}"
            )

            delete_event(
                service,
                appointment.google_event_id
            )

        except Exception as e:
            logger.exception("Google delete failed")