"""Port of routes/visitors.js + controllers/visitorController.js."""
import os

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.db import get_db
from config.event_config import EVENT
from middleware.rate_limit import rate_limit
from models.visitor import VisitorRegisterRequest, new_visitor_document
from utils.email_templates import visitor_email_html
from utils.generate_code import generate_registration_code
from utils.id_card_image import build_visitor_id_card_png
from utils.invitation_card import build_visitor_invitation_pdf
from utils.mailer import send_mail
from utils.whatsapp import send_whatsapp

router = APIRouter(prefix="/api/visitors", tags=["visitors"])

_register_limiter = rate_limit(
    "register-visitor",
    max_requests=15,
    window_seconds=15 * 60,
    message="Too many registration attempts. Please try again later.",
)


def _public_backend_url(relative_path: str) -> str:
    base = (os.environ.get("PUBLIC_BACKEND_URL") or "").rstrip("/")
    return f"{base}{relative_path}"


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
        id_card = None
        try:
            id_card = await build_visitor_id_card_png(doc)
        except Exception as card_err:  # noqa: BLE001
            print("[visitor] Failed to generate ID card image:", card_err)

        try:
            pdf_buffer = build_visitor_invitation_pdf(doc)
            attachments = [{
                "filename": f"ROAR-Expo-Invitation-{registration_code}.pdf",
                "content": pdf_buffer,
                "contentType": "application/pdf",
            }]
            if id_card:
                attachments.append({
                    "filename": f"ROAR-Expo-ID-Card-{registration_code}.png",
                    "content": id_card["buffer"],
                    "contentType": "image/png",
                    "cid": "idcard",
                })

            await send_mail(
                to=doc["email"],
                bcc=os.environ.get("ADMIN_NOTIFY_EMAIL"),
                subject=f"You're Invited! {EVENT['eventName']}",
                html=visitor_email_html(doc, has_id_card_image=bool(id_card)),
                attachments=attachments,
            )
            await db.visitors.update_one({"_id": doc["_id"]}, {"$set": {"emailSent": True}})
        except Exception as mail_err:  # noqa: BLE001
            print("[visitor] Failed to send invitation email:", mail_err)
            await db.visitors.update_one({"_id": doc["_id"]}, {"$set": {"emailError": str(mail_err)}})

        # WhatsApp delivery — non-blocking and safe to skip entirely until a
        # provider is configured (see utils/whatsapp.py).
        if id_card:
            try:
                result_wa = await send_whatsapp(
                    to=doc["phone"],
                    caption=(
                        f"You're invited to {EVENT['eventName']}! Your registration ID is {registration_code}. "
                        "Show this QR code at the entrance for quick check-in."
                    ),
                    media_url=_public_backend_url(id_card["public_url"]),
                )
                await db.visitors.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {
                        "whatsappSent": bool(result_wa.get("sent")),
                        "whatsappError": "" if result_wa.get("sent") else (result_wa.get("reason") or ""),
                    }},
                )
            except Exception as wa_err:  # noqa: BLE001
                print("[visitor] Failed to send WhatsApp message:", wa_err)
                await db.visitors.update_one({"_id": doc["_id"]}, {"$set": {"whatsappError": str(wa_err)}})

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
