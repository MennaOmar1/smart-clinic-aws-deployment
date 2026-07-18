import secrets

from fastapi import HTTPException, Request

from core.elevenlabs_config import (
    ELEVENLABS_SERVICE_HEADER,
    get_elevenlabs_service_token,
)


def require_elevenlabs_static_token(request: Request):
    expected_token = get_elevenlabs_service_token()
    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "ELEVENLABS_AUTH_NOT_CONFIGURED",
                "message": "ElevenLabs service token is not configured",
            },
        )

    provided_token = request.headers.get(ELEVENLABS_SERVICE_HEADER)
    auth_header = request.headers.get("Authorization", "")
    if not provided_token and auth_header.lower().startswith("bearer "):
        provided_token = auth_header[7:].strip()

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "UNAUTHORIZED",
                "message": "Missing or invalid ElevenLabs service token",
            },
        )

    return True
