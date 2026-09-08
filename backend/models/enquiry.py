"""Port of models/Enquiry.js — a general enquiry from the public Enquiry
page (not a registration). Emailed to the organizing team and listed in the
admin dashboard's Enquiries tab, where an admin can mark it handled."""
from pydantic import BaseModel, EmailStr, field_validator
from models.common import utcnow

ENQUIRY_STATUS_VALUES = ["new", "handled"]
ENQUIRY_CSV_COLUMNS = ["name", "email", "mobile", "details", "status", "handledAt", "emailSent", "createdAt"]


class EnquiryRequest(BaseModel):
    name: str
    email: EmailStr
    mobile: str
    details: str

    @field_validator("name")
    @classmethod
    def name_required(cls, v):
        if not v or not v.strip():
            raise ValueError("Name is required")
        return v.strip()

    @field_validator("mobile")
    @classmethod
    def mobile_min_len(cls, v):
        if not v or len(v.strip()) < 7:
            raise ValueError("A valid mobile number is required")
        return v.strip()

    @field_validator("details")
    @classmethod
    def details_len(cls, v):
        v = (v or "").strip()
        if len(v) < 5:
            raise ValueError("Please describe your enquiry")
        if len(v) > 4000:
            raise ValueError("Enquiry is too long")
        return v


def new_enquiry_document(payload: EnquiryRequest) -> dict:
    now = utcnow()
    return {
        "name": payload.name,
        "email": payload.email.strip().lower(),
        "mobile": payload.mobile,
        "details": payload.details,
        "status": "new",
        "handledAt": None,
        "emailSent": False,
        "emailError": "",
        "createdAt": now,
        "updatedAt": now,
    }
