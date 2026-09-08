"""
Port of models/Admin.js. This project talks to MongoDB directly through
Motor (no ODM), so this module holds the admin "shape" as plain constants/
helpers plus the Pydantic request schemas used to validate incoming JSON —
there's no Admin *class* mirroring a Mongoose model, since a raw dict is the
document.
"""
from pydantic import BaseModel, EmailStr, field_validator

# Permissions an admin account can hold. An admin can be granted any
# combination of these (except "all", which is exclusive and always implies
# every other permission — see has_permission() below).
#
# "all"             — full access: everything, plus managing other admins
# "exhibitors"       — exhibitor registrations: view, edit, approve/reject
# "stall-inventory"  — stall list & venue map management ("Stalls & Map" tab)
# "visitors"         — visitor registrations: view/search/export + check-in
# "scanning"         — gate-staff access: QR/code check-in only, no visitor
#                       list or export
# "invoicing"        — generate/view stall booking-summary invoices
# "enquiries"        — read/handle general enquiries from the public Enquiry page
PERMISSIONS = ["all", "exhibitors", "stall-inventory", "visitors", "scanning", "invoicing", "enquiries"]


def has_permission(permissions: list[str] | None, permission: str) -> bool:
    """True if `permissions` holds `permission`, or holds "all" (which grants
    everything). Mirrors Admin.prototype.hasPermission from the old model."""
    permissions = permissions or []
    return "all" in permissions or permission in permissions


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    permissions: list[str]

    @field_validator("permissions")
    @classmethod
    def non_empty(cls, v):
        if not v:
            raise ValueError("At least one permission is required")
        return v
