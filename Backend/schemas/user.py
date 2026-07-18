from pydantic import BaseModel, EmailStr
from typing import Literal


class UserCreate(BaseModel):
    email: EmailStr
    role: Literal["doctor", "receptionist", "admin"]


class UserUpdateRole(BaseModel):
    role: Literal["doctor", "receptionist", "admin"]


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool