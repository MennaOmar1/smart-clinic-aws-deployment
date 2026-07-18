import logging
import os
import json

from fastapi import APIRouter, Request, HTTPException, Depends
from authlib.integrations.base_client.errors import OAuthError
from fastapi.responses import RedirectResponse
from core.oauth import oauth
from core.security import create_access_token
from sqlalchemy.orm import Session

from core.database import get_db
from models.db_models import User, Doctor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Google Auth"])


# =========================
# LOGIN
# =========================
@router.get("/login")
async def login(request: Request):

    redirect_uri = os.getenv(
        "GOOGLE_CALLBACK_URL",
        "https://smart-clinic-system-production-a856.up.railway.app/auth/google/callback"
    )

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        access_type="offline",
        prompt="consent"
    )


# =========================
# CALLBACK
# =========================
@router.get("/callback")
async def auth_callback(
    request: Request,
    db: Session = Depends(get_db)
):

    print("REQUEST APP:", request.app)
    print("COOKIE HEADER:", request.headers.get("cookie"))
    print("SESSION:", dict(request.session))

    try:

        # 🔥 GET TOKEN
        token = await oauth.google.authorize_access_token(
            request,
            claims_options={}
        )

        print("TOKEN RECEIVED:", token)

        # 🔥 GET USER INFO MANUALLY
        resp = await oauth.google.get(
            "userinfo",
            token=token
        )

        user_info = resp.json()

        print("USER INFO:", user_info)

    except OAuthError as err:

        error_code = getattr(err, "error", "oauth_error")
        error_description = getattr(err, "description", str(err))
        error_uri = getattr(err, "error_uri", None)

        logger.error(
            "Google OAuth failed: %s %s %s",
            error_code,
            error_description,
            error_uri
        )

        detail = f"Google OAuth error: {error_code} - {error_description}"

        if error_uri:
            detail += f" ({error_uri})"

        raise HTTPException(status_code=400, detail=detail)

    except Exception as e:

        logger.exception("Unexpected Google OAuth error")

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # =========================
    # USER
    # =========================
    email = user_info["email"]

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user:

        user = User(
            email=email,
            name=user_info.get("name"),
            role="receptionist",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # =========================
    # SAVE GOOGLE TOKEN
    # =========================
    google_token_data = {
        "token": token.get("access_token"),
        "refresh_token": token.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "scopes": [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ]
    }

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user.id
    ).first()

    if doctor:

        doctor.google_token = json.dumps(
            google_token_data
        )

        db.commit()

        print("✅ GOOGLE TOKEN SAVED FOR DOCTOR:", doctor.id)

    else:

        print("⚠️ NO DOCTOR LINKED TO THIS USER")

    # =========================
    # APP JWT
    # =========================
    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "email": user.email
    })

    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "https://smart-clinic-system-production-a856.up.railway.app"
    )
    print("APP JWT:", access_token)
    redirect_url = (
        f"{FRONTEND_URL}/auth/callback"
        f"?token={access_token}"
        f"&role={user.role}"
    )

    return RedirectResponse(url=redirect_url)