"""Port of routes/visitors.js + controllers/visitorController.js."""
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.db import get_db
from config.event_config import EVENT
from middleware.rate_limit import rate_limit
from models.visitor import VisitorRegisterRequest, new_visitor_document
from utils.email_templates import visitor_alert_html
from utils.generate_code import generate_registration_code
from utils.notify import notify_organizers
from utils.visitor_pass import send_visitor_pass

router = APIRouter(prefix="/api/visitors", tags=["visitors"])

_register_limiter = rate_limit(
    "register-visitor",
    max_requests=40,
    window_seconds=15 * 60,
    message="Too many registration attempts. Please try again later.",
)


@router.post("/register", dependencies=[Depends(_register_limiter)])
async def register_visitor(payload: VisitorRegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        registration_code = generate_registration_code("VIS")
        doc = new_visitor_document(payload, registration_code)
        result = await db.visitors.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Build the ID card once and reuse it for both the email (inline
        # image + PDF attachment) and WhatsApp (image message) — both encode
        # the same QR (the visitor's registration code) for entrance scanning.
        # ID card + invitation PDF by e-mail, ID card on WhatsApp (production
        # BhashSMS template) — shared with the chat bot's "resend my pass" and
        # the admin "Resend pass" button (utils/visitor_pass.py).
        await send_visitor_pass(db, doc)

        await notify_organizers(
            kind="visitor",
            subject=f"New visitor: {doc['fullName']} ({EVENT['eventName']})",
            html=visitor_alert_html(doc),
        )

        return {
            "success": True,
            "message": "Registration successful. Your ID card with a QR code has been emailed to you.",
            "data": {"registrationCode": registration_code},
        }
    except HTTPException:
        raise
    except Exception as err:  # noqa: BLE001
        print("[visitor] registration error:", err)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
