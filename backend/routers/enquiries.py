"""Port of routes/enquiries.js + the public half of controllers/
enquiryController.js — the public "Enquiry" page form. Admin-side listing/
handling lives under /api/admin/enquiries (see routers/admin.py)."""
import os

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.db import get_db
from config.event_config import EVENT
from middleware.rate_limit import rate_limit
from models.enquiry import EnquiryRequest, new_enquiry_document
from utils.email_templates import enquiry_acknowledgement_html, enquiry_notification_html
from utils.mailer import send_mail
from utils.notify import organizer_recipients

router = APIRouter(prefix="/api/enquiries", tags=["enquiries"])


_enquiry_limiter = rate_limit(
    "enquiry", max_requests=10, window_seconds=15 * 60,
    message="Too many enquiries sent. Please try again later.",
)


def enquiry_recipients() -> str:
    # Where new enquiries are emailed — ORGANIZER_NOTIFY_EMAILS / ENQUIRY_NOTIFY_EMAILS
    # in .env, else the built-in admin@/mkt@ inboxes (see utils/notify.py).
    return organizer_recipients()


def auto_reply_enabled() -> bool:
    return (os.environ.get("ENQUIRY_AUTO_REPLY") or "true").strip().lower() not in ("false", "0", "off", "no")


@router.post("", dependencies=[Depends(_enquiry_limiter)])
@router.post("/", dependencies=[Depends(_enquiry_limiter)], include_in_schema=False)
async def submit_enquiry(payload: EnquiryRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        doc = new_enquiry_document(payload)
        result = await db.enquiries.insert_one(doc)
        doc["_id"] = result.inserted_id

        # Notify the organizing team. A mail failure is recorded but never
        # blocks the submission — the enquiry is already saved and visible in
        # the admin dashboard either way.
        try:
            await send_mail(
                to=enquiry_recipients(),
                subject=f"New Enquiry — {EVENT['eventName']} ({doc['name']})",
                html=enquiry_notification_html(doc),
            )
            await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"emailSent": True}})
        except Exception as mail_err:  # noqa: BLE001
            print("[enquiry] Failed to send notification email:", mail_err)
            await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"emailError": str(mail_err)}})

        # Friendly confirmation back to the sender (ENQUIRY_AUTO_REPLY=false to turn off).
        if auto_reply_enabled():
            try:
                await send_mail(
                    to=doc["email"],
                    subject=f"We've received your enquiry — {EVENT['eventName']}",
                    html=enquiry_acknowledgement_html(doc),
                )
                await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"ackSent": True}})
            except Exception as mail_err:  # noqa: BLE001
                print("[enquiry] Failed to send acknowledgement email:", mail_err)
                await db.enquiries.update_one({"_id": doc["_id"]}, {"$set": {"ackError": str(mail_err)}})

        return {
            "success": True,
            "message": "Thanks — your enquiry has been sent. Our team will get back to you shortly.",
            "data": {"id": str(doc["_id"])},
        }
    except HTTPException:
        raise
    except Exception as err:  # noqa: BLE001
        print("[enquiry] submit error:", err)
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
