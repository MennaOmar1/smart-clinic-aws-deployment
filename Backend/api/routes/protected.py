from fastapi import APIRouter, Depends
from api.deps import get_current_user, require_roles

router = APIRouter()

@router.get("/protected")
def protected(user = Depends(get_current_user)):
    return {
        "message": "You are authenticated",
        "user": user
    }

@router.get("/doctor/dashboard")
def doctor_dashboard(user = Depends(require_roles(["doctor"]))):
    return {
        "message": "Welcome Doctor",
        "user": user
    }

@router.get("/receptionist/dashboard")
def receptionist_dashboard(user = Depends(require_roles(["receptionist", "admin"]))):
    return {
        "message": "Welcome Receptionist",
        "user": user
    }