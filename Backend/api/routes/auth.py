from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.db_models import User
from core.security import verify_password, create_access_token
from schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(data.password, user.password):
        raise HTTPException(401, "Invalid credentials")

    access_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "email": user.email
    }, token_type="access")

    refresh_token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "email": user.email
    }, token_type="refresh")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }