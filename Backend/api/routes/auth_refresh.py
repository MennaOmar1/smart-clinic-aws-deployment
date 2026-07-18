from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.security import decode_token, create_access_token

class RefreshTokenRequest(BaseModel):
    refresh_token: str

router = APIRouter(prefix="/auth")


@router.post("/refresh")
def refresh_token(request: RefreshTokenRequest):
    try:
        payload = decode_token(request.refresh_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = create_access_token({
        "sub": payload["sub"],
        "role": payload["role"],
        "email": payload.get("email")
    }, token_type="access")

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }