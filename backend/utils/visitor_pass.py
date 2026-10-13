"""Builds and delivers a visitor's entry pass — the ID card (PNG with the
registration-code QR) + invitation PDF by e-mail, and the ID card image on
WhatsApp when a provider is configured.

Used by the public registration route (first send), the "Ask ROAR Anything"
bot ("resend my pass" / after a visitor edits their details) and the admin
record page ("Resend pass"). One code path, so all three behave the same and
the emailSent / whatsappSent flags on the visitor document stay accurate."""
import os

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.event_config import EVENT
from utils.email_templates import visitor_email_html
from utils.id_card_image import build_visitor_id_card_png
from utils.invitation_card import build_visitor_invitation_pdf
from utils.mailer import send_mail
from utils import whatsapp_service as wa_service


def public_backend_url(relative_path: str) -> str:
    base = (os.environ.get("PUBLIC_BACKEND_URL") or "").rstrip("/")
    # Files are reachable under /api/uploads too — the only path hosts such as
    # Emergent forward to the backend.
    if relative_path.startswith("/uploads/"):
        relative_path = "/api" + relative_path
    return f"{base}{relative_path}"


async def send_visitor_pass(db: AsyncIOMotorDatabase, doc: dict, *, resend: bool = False) -> dict:
    """Sends the pass for `doc` (a full visitor document) and records the
    outcome on it. Never raises — delivery problems are stored on the record
    (emailError / whatsappError) and returned, so registration itself is
    never lost because of a mail or WhatsApp hiccup."""
    code = doc["registrationCode"]
    result = {"emailSent": False, "emailError": "", "whatsappSent": False, "whatsappError": ""}

    id_card = None
    try:
        id_card = await build_visitor_id_card_png(doc)
    except Exception as card_err:  # noqa: BLE001
        print("[visitor] Failed to generate ID card image:", card_err)

    # ---- e-mail: invitation PDF + ID card image (inline and attached)
    try:
        pdf_buffer = build_visitor_invitation_pdf(doc)
        attachments = [{
            "filename": f"ROAR-Expo-Invitation-{code}.pdf",
            "content": pdf_buffer,
            "contentType": "application/pdf",
        }]
        if id_card:
            attachments.append({
                "filename": f"ROAR-Expo-ID-Card-{code}.png",
                "content": id_card["buffer"],
                "contentType": "image/png",
                "cid": "idcard",
            })
        subject = f"You're Invited! {EVENT['eventName']}"
        if resend:
            subject = f"Your entry pass (re-sent) — {EVENT['eventName']}"
        await send_mail(
            to=doc["email"],
            bcc=None if resend else os.environ.get("ADMIN_NOTIFY_EMAIL"),
            subject=subject,
            html=visitor_email_html(doc, has_id_card_image=bool(id_card)),
            attachments=attachments,
        )
        result["emailSent"] = True
    except Exception as mail_err:  # noqa: BLE001
        print("[visitor] Failed to send invitation email:", mail_err)
        result["emailError"] = str(mail_err)

    # ---- WhatsApp: the DLT-approved "visitor_registration" template through
    # the production BhashSMS service (admin → WhatsApp tab), ID card attached.
    # Logged in whatsapp_logs like every other send; skipped while disabled.
    if id_card:
        try:
            wa = await wa_service.send_event(
                db, "visitor_registration",
                to=doc.get("phone"),
                variables=[doc.get("fullName") or "there", code],
                recipient_type="visitor", recipient_name=doc.get("fullName"),
                media_url=public_backend_url(id_card["public_url"]),
            )
            result["whatsappSent"] = bool(wa.get("sent"))
            result["whatsappError"] = "" if wa.get("sent") else (wa.get("reason") or "")
        except Exception as wa_err:  # noqa: BLE001
            print("[visitor] Failed to send WhatsApp message:", wa_err)
            result["whatsappError"] = str(wa_err)

    updates = dict(result)
    if resend:
        from models.common import utcnow
        updates["passResentAt"] = utcnow()
    await db.visitors.update_one({"_id": doc["_id"]}, {"$set": updates})
    return result
