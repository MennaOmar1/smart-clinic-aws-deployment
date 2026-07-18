import unittest
import os
import sys
import types
from unittest.mock import patch
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


database_stub = types.ModuleType("core.database")
database_stub.Base = declarative_base()


def _test_get_db():
    raise RuntimeError("Test database dependency must be overridden")


database_stub.get_db = _test_get_db
sys.modules["core.database"] = database_stub


from api.routes import elevenlabs as elevenlabs_routes
from models.db_models import Appointment, Base, Doctor, User
from services.elevenlabs_scheduling_service import (
    ElevenLabsSchedulingError,
    ElevenLabsSchedulingService,
)


CAIRO = ZoneInfo("Africa/Cairo")


class ElevenLabsSchedulingServiceTests(unittest.TestCase):

    def setUp(self):

        self.engine = create_engine("sqlite:///:memory:")

        Base.metadata.create_all(bind=self.engine)

        self.SessionLocal = sessionmaker(bind=self.engine)

        self.db = self.SessionLocal()

        user = User(
            id=1,
            name="Dr. Ahmed Hassan",
            email="ahmed@example.com",
            role="doctor"
        )

        doctor = Doctor(
            id=1,
            user_id=1,
            specialization="Cardiology",
            google_token='{"token":"fake"}'
        )

        self.db.add_all([user, doctor])

        self.db.commit()

    def tearDown(self):

        self.db.close()

        self.engine.dispose()

    def test_reports_available_for_valid_future_cairo_slot(self):

        result = ElevenLabsSchedulingService.check_availability(
            self.db,
            doctor_id=1,
            requested_time=datetime(
                2026,
                5,
                12,
                10,
                0,
                tzinfo=CAIRO
            ),
            now=datetime(
                2026,
                5,
                11,
                12,
                0,
                tzinfo=CAIRO
            ),
        )

        self.assertTrue(result["is_available"])

        self.assertEqual(result["error_code"], None)

        self.assertEqual(
            result["normalized_time"],
            "2026-05-12T10:00:00+03:00"
        )

    def test_rejects_non_30_minute_slot_alignment(self):

        result = ElevenLabsSchedulingService.check_availability(
            self.db,
            doctor_id=1,
            requested_time=datetime(
                2026,
                5,
                12,
                10,
                15,
                tzinfo=CAIRO
            ),
            now=datetime(
                2026,
                5,
                11,
                12,
                0,
                tzinfo=CAIRO
            ),
        )

        self.assertFalse(result["is_available"])

        self.assertEqual(
            result["error_code"],
            "INVALID_SLOT_ALIGNMENT"
        )

    def test_booking_creates_conflict_free_appointment_and_blocks_duplicate(self):

        start = datetime(
            2026,
            5,
            12,
            10,
            0,
            tzinfo=CAIRO
        )

        with patch(
            "services.calendar_sync_service.CalendarSyncService.create"
        ) as mock_calendar:

            mock_calendar.return_value = "fake-google-event-id"

            created = ElevenLabsSchedulingService.book_appointment(
                self.db,
                doctor_id=1,
                requested_time=start,
                patient_name="Eleven Test",
                patient_phone="01012345678",
                notes="voice booking",
                now=datetime(
                    2026,
                    5,
                    11,
                    12,
                    0,
                    tzinfo=CAIRO
                ),
            )

        self.assertTrue(created["booking_success"])

        self.assertIsInstance(
            created["appointment_id"],
            int
        )

        stored = (
            self.db.query(Appointment)
            .filter(
                Appointment.id == created["appointment_id"]
            )
            .one()
        )

        self.assertEqual(
            stored.start_time,
            start.replace(tzinfo=None)
        )

        self.assertEqual(
            stored.end_time,
            start.replace(tzinfo=None)
            + timedelta(minutes=30)
        )

        with self.assertRaises(
            ElevenLabsSchedulingError
        ) as raised:

            ElevenLabsSchedulingService.book_appointment(
                self.db,
                doctor_id=1,
                requested_time=start,
                patient_name="Eleven Test Two",
                patient_phone="01087654321",
                now=datetime(
                    2026,
                    5,
                    11,
                    12,
                    0,
                    tzinfo=CAIRO
                ),
            )

        self.assertEqual(
            raised.exception.status_code,
            409
        )

        self.assertEqual(
            raised.exception.payload["error_code"],
            "SLOT_CONFLICT"
        )

        self.assertFalse(
            raised.exception.payload["booking_success"]
        )


class ElevenLabsRouteValidationTests(unittest.TestCase):

    def setUp(self):

        os.environ["ELEVENLABS_SERVICE_TOKEN"] = "test-token"

        self.app = FastAPI()

        self.app.include_router(
            elevenlabs_routes.router
        )

        self.app.dependency_overrides[
            elevenlabs_routes.get_db
        ] = lambda: None

        self.client = TestClient(self.app)

    def tearDown(self):

        os.environ.pop(
            "ELEVENLABS_SERVICE_TOKEN",
            None
        )

    def test_booking_validation_error_keeps_elevenlabs_mapping_paths(self):

        response = self.client.post(
            "/elevenlabs/book",
            headers={
                "X-ElevenLabs-Service-Token": "test-token"
            },
            json={
                "doctor_id": 1,
                "patient_name": "A",
                "patient_phone": "123",
                "time": "not-a-date",
            },
        )

        self.assertEqual(
            response.status_code,
            422
        )

        body = response.json()

        self.assertFalse(body["booking_success"])

        self.assertEqual(
            body["booking_confirmation"],
            body["message"]
        )

        self.assertEqual(
            body["appointment_id"],
            None
        )

        self.assertEqual(
            body["error_code"],
            "VALIDATION_ERROR"
        )

    def test_missing_booking_body_keeps_elevenlabs_mapping_paths(self):

        response = self.client.post(
            "/elevenlabs/book",
            headers={
                "X-ElevenLabs-Service-Token": "test-token"
            },
        )

        self.assertEqual(
            response.status_code,
            422
        )

        body = response.json()

        self.assertFalse(
            body["booking_success"]
        )

        self.assertEqual(
            body["error_code"],
            "VALIDATION_ERROR"
        )

    def test_availability_validation_error_keeps_elevenlabs_mapping_paths(self):

        response = self.client.get(
            "/elevenlabs/availability",
            headers={
                "X-ElevenLabs-Service-Token": "test-token"
            },
            params={
                "doctor_id": "x",
                "time": "not-a-date"
            },
        )

        self.assertEqual(
            response.status_code,
            422
        )

        body = response.json()

        self.assertFalse(
            body["is_available"]
        )

        self.assertEqual(
            body["availability_message"],
            body["message"]
        )

        self.assertEqual(
            body["error_code"],
            "VALIDATION_ERROR"
        )


if __name__ == "__main__":
    unittest.main()