import os


ELEVENLABS_TIMEZONE = "Africa/Cairo"
ELEVENLABS_WORK_START = "08:00"
ELEVENLABS_WORK_END = "17:00"
ELEVENLABS_SLOT_MINUTES = 30
ELEVENLABS_SERVICE_TOKEN_ENV = "ELEVENLABS_SERVICE_TOKEN"
ELEVENLABS_SERVICE_HEADER = os.getenv(
    "ELEVENLABS_SERVICE_HEADER",
    "X-ElevenLabs-Service-Token",
)


def get_elevenlabs_service_token() -> str | None:
    token = os.getenv(ELEVENLABS_SERVICE_TOKEN_ENV)
    if not token:
        return None
    return token.strip()
