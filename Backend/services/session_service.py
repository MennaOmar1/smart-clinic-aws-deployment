import json
from core.redis_client import r

class SessionService:

    @staticmethod
    def init():
        return {
            "state": "medical_assessment",
            "current_complaint": None,
            "history": [],
            "data": {
                "age": None,
                "gender": None
            },
            "booking": {
                "doctor_id": None,
                "specialization": None,
                "date": None,
                "slot": None
            },
            "doctors": [],
            "slots": []
        }

    @staticmethod
    def get(user_id):
        data = r.get(str(user_id))
        return json.loads(data) if data else None

    @staticmethod
    def get_or_create(user_id):
        session = SessionService.get(user_id)
        if not session:
            session = SessionService.init()
            SessionService.update(user_id, session)
        return session

    @staticmethod
    def update(user_id, session):
        r.set(str(user_id), json.dumps(session))

    @staticmethod
    def reset(user_id):
        r.delete(str(user_id))