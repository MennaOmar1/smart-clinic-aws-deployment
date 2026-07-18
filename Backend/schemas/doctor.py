from pydantic import BaseModel


class DoctorProfileUpdate(BaseModel):
    name: str | None = None
    specialization: str | None = None
    bio: str | None = None
    phone: str | None = None
    experience: str | None = None
    image_url: str | None = None