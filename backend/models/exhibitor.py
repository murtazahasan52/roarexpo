"""
Port of models/Exhibitor.js (post crane/stall-type removal — see README §8).
Defines the exhibitor document's default shape (Mongoose used to fill these
in automatically; Motor does not, so we do it explicitly on insert) and the
request-validation rules that used to live in express-validator chains in
routes/exhibitors.js.
"""
from models.common import utcnow

STATUS_VALUES = ["pending", "confirmed", "cancelled"]

# Fields an admin may edit from the dashboard (PATCH /admin/exhibitors/:id).
# Deliberately excludes registrationCode, status (use approve/reject),
# emailSent/emailError, whatsappSent/whatsappError, logoUrl/productImages
# (file uploads aren't handled by this endpoint), and agreedToTerms.
EDITABLE_EXHIBITOR_FIELDS = [
    "itsNumber",
    "contactPerson",
    "designation",
    "email",
    "phone",
    "landline",
    "whatsapp",
    "companyName",
    "businessAddress",
    "businessEmail",
    "city",
    "state",
    "pincode",
    "website",
    "gstNumber",
    "linkedin",
    "instagram",
    "facebook",
    "category",
    "productsServices",
    "message",
    "stallPackage",
    "numberOfStalls",
    "fasciaName",
]

# Columns for the CSV export (adminController.exportExhibitorsCSV).
EXHIBITOR_CSV_COLUMNS = [
    "registrationCode",
    "itsNumber",
    "companyName",
    "contactPerson",
    "designation",
    "email",
    "phone",
    "landline",
    "whatsapp",
    "businessAddress",
    "businessEmail",
    "city",
    "state",
    "pincode",
    "website",
    "linkedin",
    "instagram",
    "facebook",
    "category",
    "stallPackage",
    "stallNumber",
    "stallRate",
    "numberOfStalls",
    "fasciaName",
    "gstNumber",
    "status",
    "emailSent",
    "whatsappSent",
    "createdAt",
]


def new_exhibitor_document(fields: dict) -> dict:
    """Builds a full exhibitor document with the same field defaults the old
    Mongoose schema applied automatically."""
    now = utcnow()
    return {
        "registrationCode": fields["registrationCode"],
        "itsNumber": fields.get("itsNumber", "").strip(),
        "contactPerson": fields.get("contactPerson", "").strip(),
        "designation": (fields.get("designation") or "").strip(),
        "email": (fields.get("email") or "").strip().lower(),
        "phone": (fields.get("phone") or "").strip(),
        "landline": (fields.get("landline") or "").strip(),
        "whatsapp": (fields.get("whatsapp") or "").strip(),
        "companyName": fields.get("companyName", "").strip(),
        "businessAddress": fields.get("businessAddress", "").strip(),
        "businessEmail": (fields.get("businessEmail") or "").strip().lower(),
        "city": (fields.get("city") or "").strip(),
        "state": (fields.get("state") or "").strip(),
        "pincode": (fields.get("pincode") or "").strip(),
        "website": (fields.get("website") or "").strip(),
        "gstNumber": (fields.get("gstNumber") or "").strip(),
        "linkedin": (fields.get("linkedin") or "").strip(),
        "instagram": (fields.get("instagram") or "").strip(),
        "facebook": (fields.get("facebook") or "").strip(),
        "logoUrl": fields.get("logoUrl", ""),
        "productImages": fields.get("productImages", []),
        "category": fields.get("category", ""),
        "productsServices": (fields.get("productsServices") or "").strip(),
        "message": (fields.get("message") or "").strip(),
        "stallPackage": fields.get("stallPackage", ""),
        "numberOfStalls": fields.get("numberOfStalls") or 1,
        "stallNumber": (fields.get("stallNumber") or "").strip().upper(),
        "stallId": fields.get("stallId"),
        "stallRate": fields.get("stallRate"),
        "fasciaName": (fields.get("fasciaName") or "").strip(),
        "agreedToTerms": True,
        "status": "pending",
        "emailSent": False,
        "emailError": "",
        "whatsappSent": False,
        "whatsappError": "",
        "createdAt": now,
        "updatedAt": now,
    }
