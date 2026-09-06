"""Port of models/Visitor.js."""
from pydantic import BaseModel, EmailStr, field_validator
from models.common import utcnow

VISITOR_CSV_COLUMNS = [
    "registrationCode",
    "fullName",
    "email",
    "phone",
    "city",
    "organization",
    "designation",
    "interests",
    "numberOfGuests",
    "source",
    "checkedIn",
    "checkedInAt",
    "emailSent",
    "whatsappSent",
    "createdAt",
]


class VisitorRegisterRequest(BaseModel):
    fullName: str
    email: EmailStr
    phone: str
    city: str | None = ""
    organization: str | None = ""
    designation: str | None = ""
    interests: list[str] = []
    howDidYouHear: str | None = ""
    numberOfGuests: int | None = 1
    source: str | None = "online"

    @field_validator("fullName")
    @classmethod
    def name_required(cls, v):
        if not v or not v.strip():
            raise ValueError("Full name is required")
        return v

    @field_validator("phone")
    @classmethod
    def phone_min_len(cls, v):
        if not v or len(v.strip()) < 7:
            raise ValueError("A valid phone number is required")
        return v

    @field_validator("source")
    @classmethod
    def source_valid(cls, v):
        if v and v not in ("online", "onsite"):
            raise ValueError("Invalid source")
        return v


def new_visitor_document(payload: VisitorRegisterRequest, registration_code: str) -> dict:
    now = utcnow()
    return {
        "registrationCode": registration_code,
        "fullName": payload.fullName.strip(),
        "email": payload.email.strip().lower(),
        "phone": payload.phone.strip(),
        "city": (payload.city or "").strip(),
        "organization": (payload.organization or "").strip(),
        "designation": (payload.designation or "").strip(),
        "interests": payload.interests or [],
        "howDidYouHear": (payload.howDidYouHear or "").strip(),
        "numberOfGuests": payload.numberOfGuests or 1,
        "source": payload.source if payload.source == "onsite" else "online",
        "checkedIn": False,
        "checkedInAt": None,
        "emailSent": False,
        "emailError": "",
        "whatsappSent": False,
        "whatsappError": "",
        "createdAt": now,
        "updatedAt": now,
    }
