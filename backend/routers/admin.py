"""
Port of routes/admin.js + controllers/adminController.js + the admin half of
controllers/stallController.js. One router, mirroring the old Express
router's structure/comments closely so the permission model (see
middleware/auth.py) stays easy to audit against the original.
"""
import asyncio
import csv
import io
import os
import base64
from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.db import get_db
from config.event_config import EVENT, find_stall_package
from middleware.auth import (
    AdminPayload, require_admin, require_any_resource, require_full_access, require_resource, sign_token,
)
from middleware.rate_limit import rate_limit
from middleware.upload import MAP_TYPES, STALL_MAP_MAX_BYTES, read_upload, write_upload_bytes, save_upload, EXHIBITOR_FILE_MAX_BYTES
from utils.storage import get_object
from models.admin import PERMISSIONS, AdminCreateRequest, AdminLoginRequest
from models.common import serialize_doc, serialize_list, to_object_id, utcnow
from models.enquiry import ENQUIRY_CSV_COLUMNS, ENQUIRY_STATUS_VALUES
from models.exhibitor import EDITABLE_EXHIBITOR_FIELDS, EXHIBITOR_CSV_COLUMNS, new_exhibitor_document
from models.stall import STALL_STATUS_VALUES, new_stall_document
from models.stall_map import map_payload, new_stall_map_document, parse_series
from models.visitor import VISITOR_CSV_COLUMNS
from utils.email_templates import exhibitor_approved_email_html, exhibitor_rejected_email_html, exhibitor_reopened_email_html, exhibitor_email_html
from utils.hashing import hash_password, verify_password
from utils.generate_code import generate_registration_code
from utils.invoice import build_exhibitor_invoice_pdf
from utils.pdf_to_image import pdf_first_page_to_png
from utils.layout_detect import detect_layout, suggest_package_for_prefix
from utils.mailer import send_mail
from utils.stall_holds import release_expired_holds
from utils.whatsapp import send_whatsapp
from utils import whatsapp_service as wa

router = APIRouter(prefix="/api/admin", tags=["admin"])

_login_limiter = rate_limit(
    "admin-login", max_requests=20, window_seconds=15 * 60,
    message="Too many login attempts. Please try again later.",
)


# ---------- Auth ----------

@router.post("/login", dependencies=[Depends(_login_limiter)])
async def login(payload: AdminLoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    admin = await db.admins.find_one({"email": payload.email.lower().strip()})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, admin["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = sign_token(admin)
    return {
        "success": True,
        "token": token,
        "admin": {"name": admin["name"], "email": admin["email"], "permissions": admin.get("permissions", [])},
    }


@router.get("/stats")
async def stats(admin: AdminPayload = Depends(require_admin), db: AsyncIOMotorDatabase = Depends(get_db)):
    permissions = admin.get("permissions") or []
    is_all = "all" in permissions
    can_see_exhibitors = is_all or "exhibitors" in permissions or "invoicing" in permissions
    can_see_visitors = is_all or "visitors" in permissions
    can_see_checked_in = can_see_visitors or "scanning" in permissions
    can_see_enquiries = is_all or "enquiries" in permissions

    exhibitor_count = await db.exhibitors.count_documents({}) if can_see_exhibitors else 0
    approved_exhibitor_count = await db.exhibitors.count_documents({"status": "confirmed"}) if can_see_exhibitors else 0
    pending_exhibitor_count = await db.exhibitors.count_documents({"status": "pending"}) if can_see_exhibitors else 0
    visitor_count = await db.visitors.count_documents({}) if can_see_visitors else 0
    checked_in_count = await db.visitors.count_documents({"checkedIn": True}) if can_see_checked_in else 0
    new_enquiry_count = await db.enquiries.count_documents({"status": "new"}) if can_see_enquiries else 0

    return {"success": True, "data": {
        "exhibitorCount": exhibitor_count, "approvedExhibitorCount": approved_exhibitor_count,
        "pendingExhibitorCount": pending_exhibitor_count,
        "visitorCount": visitor_count, "checkedInCount": checked_in_count,
        "newEnquiryCount": new_enquiry_count,
    }}


def _search_query(search: str, fields: list[str]) -> dict:
    if not search:
        return {}
    return {"$or": [{f: {"$regex": search.strip(), "$options": "i"}} for f in fields]}


def _to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(columns)
    for row in rows:
        line = []
        for col in columns:
            val = row.get(col, "")
            if val is None:
                val = ""
            elif isinstance(val, list):
                val = "; ".join(str(v) for v in val)
            elif isinstance(val, datetime):
                val = serialize_doc({"v": val})["v"]
            line.append(str(val))
        writer.writerow(line)
    return buf.getvalue()


# ---------- Exhibitors ----------

@router.get("/exhibitors")
async def list_exhibitors(
    search: str = "", page: int = 1, limit: int = 25,
    admin: AdminPayload = Depends(require_any_resource(["exhibitors", "invoicing"])),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = _search_query(search, ["companyName", "contactPerson", "email", "phone", "registrationCode"])
    skip = (page - 1) * limit
    total = await db.exhibitors.count_documents(query)
    items = await db.exhibitors.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(length=None)
    return {"success": True, "data": serialize_list(items), "total": total, "page": page, "limit": limit}


@router.get("/exhibitors/export")
async def export_exhibitors_csv(
    admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    items = await db.exhibitors.find().sort("createdAt", -1).to_list(length=None)
    csv_text = _to_csv(items, EXHIBITOR_CSV_COLUMNS)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=exhibitors.csv"},
    )


# One exhibitor registration in full — the admin record page.
@router.get("/exhibitors/{id}")
async def get_exhibitor(
    id: str,
    admin: AdminPayload = Depends(require_any_resource(["exhibitors", "invoicing"])),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    return {"success": True, "data": serialize_doc(exhibitor)}


@router.patch("/exhibitors/{id}")
async def edit_exhibitor(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    if not oid:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    exhibitor = await db.exhibitors.find_one({"_id": oid})
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    updates = {}
    for field in EDITABLE_EXHIBITOR_FIELDS:
        if field in payload and payload[field] is not None:
            updates[field] = payload[field]

    # Stall reassignment: only touched if `stallNumber` was included in the
    # request body and differs from what the exhibitor currently holds.
    if "stallNumber" in payload:
        requested_stall_number = str(payload.get("stallNumber") or "").strip().upper()
        current_stall_number = exhibitor.get("stallNumber") or ""

        if requested_stall_number != current_stall_number:
            previous_stall_id = exhibitor.get("stallId")

            if not requested_stall_number:
                # Admin cleared the stall assignment entirely.
                updates["stallNumber"] = ""
                updates["stallId"] = None
                updates["stallRate"] = None
            else:
                new_stall = await db.stalls.find_one({"stallNumber": requested_stall_number})
                if not new_stall:
                    raise HTTPException(status_code=404, detail="That stall could not be found.")

                claim_status = "booked" if exhibitor.get("status") == "confirmed" else "held"
                set_fields = {
                    "status": claim_status,
                    "heldBy": oid if claim_status == "held" else None,
                    "bookedBy": oid if claim_status == "booked" else None,
                }
                claimed = await db.stalls.find_one_and_update(
                    {"_id": new_stall["_id"], "status": "available"}, {"$set": set_fields}, return_document=True,
                )
                if not claimed:
                    raise HTTPException(status_code=409, detail="That stall is not available.")

                updates["stallNumber"] = new_stall["stallNumber"]
                updates["stallId"] = new_stall["_id"]
                updates["stallRate"] = new_stall["rate"]

            # Release the previously-held stall only after the new one (if
            # any) was successfully claimed, so a failed reassignment never
            # strands the exhibitor without the stall they already had.
            new_stall_id = updates.get("stallId")
            if previous_stall_id and str(previous_stall_id) != str(new_stall_id):
                await db.stalls.update_one(
                    {"_id": previous_stall_id}, {"$set": {"status": "available", "heldBy": None, "bookedBy": None}},
                )

    if updates:
        updates["updatedAt"] = utcnow()
        await db.exhibitors.update_one({"_id": oid}, {"$set": updates})

    updated = await db.exhibitors.find_one({"_id": oid})
    return {"success": True, "message": "Exhibitor updated", "data": serialize_doc(updated)}


@router.post("/exhibitors/book")
async def admin_book_stall(
    stallNumber: str = Form(""),
    stallNumbers: str = Form(""),
    amount: str = Form(""),
    itsNumber: str = Form(""),
    contactPerson: str = Form(...),
    designation: str = Form(""),
    email: str = Form(...),
    phone: str = Form(...),
    landline: str = Form(""),
    whatsapp: str = Form(""),
    companyName: str = Form(...),
    businessAddress: str = Form(""),
    businessEmail: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    website: str = Form(""),
    gstNumber: str = Form(""),
    linkedin: str = Form(""),
    instagram: str = Form(""),
    facebook: str = Form(""),
    category: str = Form(""),
    productsServices: str = Form(""),
    message: str = Form(""),
    numberOfStalls: int = Form(1),
    fasciaName: str = Form(""),
    logo: UploadFile | None = File(None),
    productImages: list[UploadFile] = File(default=[]),
    admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Admin-side stall booking: same fields as the public exhibitor form, but
    the stall is chosen beforehand (on the map). Books ANY stall — including
    admin-only Ruby — as a confirmed exhibitor with a custom amount, and sends
    the confirmation email. Multiple stalls can be booked under one exhibitor
    by passing a comma-separated `stallNumbers`."""
    raw_numbers = stallNumbers or stallNumber or ""
    stall_number_list = []
    for part in raw_numbers.replace(",", " ").split():
        up = part.strip().upper()
        if up and up not in stall_number_list:
            stall_number_list.append(up)
    if not stall_number_list:
        raise HTTPException(status_code=400, detail="Please pick at least one stall to book.")
    if not contactPerson.strip() or not email.strip() or not phone.strip() or not companyName.strip():
        raise HTTPException(status_code=400, detail="Contact name, email, mobile and company name are required.")

    await release_expired_holds(db)
    stalls = []
    for sn in stall_number_list:
        stall = await db.stalls.find_one({"stallNumber": sn})
        if not stall:
            raise HTTPException(status_code=404, detail=f"Stall {sn} could not be found.")
        if stall["status"] != "available":
            raise HTTPException(status_code=409, detail=f"Stall {sn} is not available — it may already be booked or reserved.")
        stalls.append(stall)

    first_stall = stalls[0]
    try:
        amt = int(round(float(amount))) if str(amount).strip() else sum(s.get("rate") or 0 for s in stalls)
    except (TypeError, ValueError):
        amt = sum(s.get("rate") or 0 for s in stalls)

    logo_url = ""
    if logo is not None:
        filename = await save_upload(logo, "logos", EXHIBITOR_FILE_MAX_BYTES)
        logo_url = f"/uploads/logos/{filename}"
    product_image_urls = []
    for img in productImages or []:
        if img is None:
            continue
        filename = await save_upload(img, "product-images", EXHIBITOR_FILE_MAX_BYTES)
        product_image_urls.append(f"/uploads/product-images/{filename}")

    stall_number_display = ", ".join(stall_number_list)
    registration_code = generate_registration_code("STL")
    doc = new_exhibitor_document({
        "registrationCode": registration_code,
        "itsNumber": itsNumber, "contactPerson": contactPerson, "designation": designation,
        "email": email, "phone": phone, "landline": landline, "whatsapp": whatsapp,
        "companyName": companyName, "businessAddress": businessAddress, "businessEmail": businessEmail,
        "city": city, "state": state, "pincode": pincode, "website": website, "gstNumber": gstNumber,
        "linkedin": linkedin, "instagram": instagram, "facebook": facebook,
        "logoUrl": logo_url, "productImages": product_image_urls,
        "category": category, "productsServices": productsServices, "message": message,
        "stallPackage": first_stall.get("packageCode", ""), "numberOfStalls": len(stall_number_list),
        "stallNumber": stall_number_display, "stallId": first_stall["_id"], "stallRate": amt,
        "fasciaName": fasciaName,
    })
    doc["stallNumbers"] = stall_number_list
    doc["status"] = "confirmed"

    result = await db.exhibitors.insert_one(doc)
    doc["_id"] = result.inserted_id

    claimed_ids = []
    for stall in stalls:
        claimed = await db.stalls.find_one_and_update(
            {"_id": stall["_id"], "status": "available"},
            {"$set": {"status": "booked", "bookedBy": doc["_id"], "heldBy": None, "tempHoldToken": None, "tempHoldExpiresAt": None}},
            return_document=True,
        )
        if not claimed:
            # A stall was taken between validation and claim: roll back everything.
            if claimed_ids:
                await db.stalls.update_many(
                    {"_id": {"$in": claimed_ids}},
                    {"$set": {"status": "available", "bookedBy": None, "heldBy": None}},
                )
            await db.exhibitors.delete_one({"_id": doc["_id"]})
            raise HTTPException(status_code=409, detail=f"Stall {stall['stallNumber']} was just taken. Please try again.")
        claimed_ids.append(stall["_id"])

    try:
        await send_mail(
            to=doc["email"],
            subject=f"Stall Confirmed — {EVENT['eventName']} ({registration_code})",
            html=exhibitor_approved_email_html(doc),
        )
        await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"emailSent": True}})
    except Exception as mail_err:  # noqa: BLE001
        print("[admin] Failed to send booking confirmation email:", mail_err)
        await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"emailError": str(mail_err)}})

    try:
        result_wa = await wa.send_event(
            db, "approval",
            to=doc.get("whatsapp") or doc.get("phone") or "",
            variables=[doc.get("contactPerson") or "there", stall_number_display, registration_code],
            recipient_type="exhibitor", recipient_name=doc.get("contactPerson"),
        )
        await db.exhibitors.update_one({"_id": doc["_id"]}, {"$set": {"whatsappSent": bool(result_wa.get("sent")), "whatsappError": "" if result_wa.get("sent") else (result_wa.get("reason") or "")}})
    except Exception as wa_err:  # noqa: BLE001
        print("[admin] Failed to send booking WhatsApp message:", wa_err)

    updated = await db.exhibitors.find_one({"_id": doc["_id"]})
    return {"success": True, "message": f"{stall_number_display} booked for {doc['companyName']}.", "data": serialize_doc(updated)}


@router.delete("/exhibitors/{id}")
async def delete_exhibitor(
    id: str, admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Permanently removes an exhibitor registration. Any stall it was
    holding or had booked is released back to "available" first so it can
    be re-sold."""
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    if exhibitor.get("stallId"):
        await db.stalls.update_one(
            {"_id": exhibitor["stallId"], "$or": [{"heldBy": oid}, {"bookedBy": oid}]},
            {"$set": {"status": "available", "heldBy": None, "bookedBy": None}},
        )
    # Release any additional stalls booked under this exhibitor (multi-stall bookings).
    await db.stalls.update_many(
        {"$or": [{"heldBy": oid}, {"bookedBy": oid}]},
        {"$set": {"status": "available", "heldBy": None, "bookedBy": None}},
    )
    await db.exhibitors.delete_one({"_id": oid})
    return {"success": True, "message": "Exhibitor registration deleted and its stall released"}


@router.patch("/exhibitors/{id}/payment")
async def set_payment_status(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Toggle an exhibitor's payment status (paid/unpaid) at any time."""
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    status_val = "paid" if str(payload.get("paymentStatus", "")).lower() == "paid" else "unpaid"
    await db.exhibitors.update_one({"_id": oid}, {"$set": {"paymentStatus": status_val, "updatedAt": utcnow()}})
    try:
        await wa.send_event(
            db, "payment_done" if status_val == "paid" else "unpaid",
            to=exhibitor.get("whatsapp") or exhibitor.get("phone") or "",
            variables=[exhibitor.get("contactPerson") or "there", exhibitor.get("stallNumber") or "your stall"],
            recipient_type="exhibitor", recipient_name=exhibitor.get("contactPerson"),
        )
    except Exception as wa_err:  # noqa: BLE001
        print("[admin] Failed to send payment WhatsApp message:", wa_err)
    updated = await db.exhibitors.find_one({"_id": oid})
    return {"success": True, "message": f"Marked {status_val}", "data": serialize_doc(updated)}


@router.post("/me/password")
async def change_my_password(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_admin), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Logged-in admin changes their own password (verifies current password)."""
    current = str(payload.get("currentPassword") or "")
    new = str(payload.get("newPassword") or "")
    confirm = str(payload.get("confirmPassword") or "")
    if not current or not new:
        raise HTTPException(status_code=400, detail="Current and new password are required.")
    if new != confirm:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    if len(new) < 8 or len(new.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    account = await db.admins.find_one({"_id": to_object_id(admin.get("id"))})
    if not account or not verify_password(current, account["passwordHash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if verify_password(new, account["passwordHash"]):
        raise HTTPException(status_code=400, detail="New password must be different from the current one.")
    await db.admins.update_one({"_id": account["_id"]}, {"$set": {"passwordHash": hash_password(new), "updatedAt": utcnow()}})
    return {"success": True, "message": "Password changed successfully."}


@router.post("/admins/{id}/password")
async def reset_admin_password(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Super-admin ('all') resets another admin's password."""
    new = str(payload.get("newPassword") or "")
    confirm = str(payload.get("confirmPassword") or "")
    if new != confirm:
        raise HTTPException(status_code=400, detail="New passwords do not match.")
    if len(new) < 8 or len(new.encode("utf-8")) > 72:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters.")
    oid = to_object_id(id)
    target = await db.admins.find_one({"_id": oid}) if oid else None
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")
    await db.admins.update_one({"_id": oid}, {"$set": {"passwordHash": hash_password(new), "updatedAt": utcnow()}})
    return {"success": True, "message": f"Password reset for {target.get('name') or target.get('email')}."}


@router.post("/exhibitors/{id}/approve")
async def approve_exhibitor(
    id: str, payload: dict = Body(default={}),
    admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    if exhibitor["status"] == "confirmed":
        return {"success": True, "message": "Already confirmed", "data": serialize_doc(exhibitor)}

    payment_status = "paid" if str((payload or {}).get("paymentStatus", "")).lower() == "paid" else "unpaid"
    approved_by = {"id": admin.get("id"), "name": admin.get("name"), "email": admin.get("email")}
    await db.exhibitors.update_one({"_id": oid}, {"$set": {
        "status": "confirmed", "paymentStatus": payment_status,
        "approvedBy": approved_by, "approvedByName": admin.get("name"), "approvedAt": utcnow(),
        "updatedAt": utcnow(),
    }})

    if exhibitor.get("stallId"):
        await db.stalls.update_one(
            {"_id": exhibitor["stallId"]}, {"$set": {"status": "booked", "bookedBy": oid, "heldBy": None}},
        )

    try:
        await send_mail(
            to=exhibitor["email"],
            subject=f"Stall Confirmed — ROAR Expo ({exhibitor['registrationCode']})",
            html=exhibitor_approved_email_html(exhibitor),
        )
    except Exception as mail_err:  # noqa: BLE001
        print("[admin] Failed to send approval email:", mail_err)

    try:
        result_wa = await wa.send_event(
            db, "approval",
            to=exhibitor.get("whatsapp") or exhibitor["phone"],
            variables=[exhibitor.get("contactPerson") or "there", exhibitor.get("stallNumber") or "your stall", exhibitor["registrationCode"]],
            recipient_type="exhibitor", recipient_name=exhibitor.get("contactPerson"),
        )
        await db.exhibitors.update_one(
            {"_id": oid},
            {"$set": {
                "whatsappSent": bool(result_wa.get("sent")),
                "whatsappError": "" if result_wa.get("sent") else (result_wa.get("reason") or ""),
            }},
        )
    except Exception as wa_err:  # noqa: BLE001
        print("[admin] Failed to send approval WhatsApp message:", wa_err)

    updated = await db.exhibitors.find_one({"_id": oid})
    return {"success": True, "message": "Exhibitor approved", "data": serialize_doc(updated)}


@router.post("/exhibitors/{id}/reject")
async def reject_exhibitor(
    id: str, admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    await db.exhibitors.update_one({"_id": oid}, {"$set": {"status": "cancelled", "updatedAt": utcnow()}})

    # Release the stall so it is bookable again immediately.
    if exhibitor.get("stallId"):
        await db.stalls.update_one(
            {"_id": exhibitor["stallId"], "$or": [{"heldBy": oid}, {"bookedBy": oid}]},
            {"$set": {"status": "available", "heldBy": None, "bookedBy": None, "tempHoldToken": None, "tempHoldExpiresAt": None,
                      "updatedAt": utcnow()}},
        )
    # Release any additional stalls booked under this exhibitor (multi-stall bookings).
    await db.stalls.update_many(
        {"$or": [{"heldBy": oid}, {"bookedBy": oid}]},
        {"$set": {"status": "available", "heldBy": None, "bookedBy": None, "tempHoldToken": None, "tempHoldExpiresAt": None,
                  "updatedAt": utcnow()}},
    )

    # Tell the exhibitor, with a link to register again.
    try:
        await send_mail(
            to=exhibitor["email"],
            subject=f"About your stall registration — {EVENT['eventName']}",
            html=exhibitor_rejected_email_html(exhibitor),
        )
    except Exception as mail_err:  # noqa: BLE001
        print("[exhibitor] Failed to send rejection email:", mail_err)

    try:
        await wa.send_event(
            db, "rejection",
            to=exhibitor.get("whatsapp") or exhibitor.get("phone") or "",
            variables=[exhibitor.get("contactPerson") or "there", exhibitor.get("registrationCode") or ""],
            recipient_type="exhibitor", recipient_name=exhibitor.get("contactPerson"),
        )
    except Exception as wa_err:  # noqa: BLE001
        print("[admin] Failed to send rejection WhatsApp message:", wa_err)

    updated = await db.exhibitors.find_one({"_id": oid})
    return {"success": True, "message": "Exhibitor rejected, stall released and the exhibitor notified", "data": serialize_doc(updated)}


# Reopen a rejected registration: pending again, the original stall is
# re-held if it is still free, and the exhibitor is asked to review /
# complete their details.
@router.post("/exhibitors/{id}/reopen")
async def reopen_exhibitor(
    id: str, admin: AdminPayload = Depends(require_resource("exhibitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")
    if exhibitor["status"] != "cancelled":
        raise HTTPException(status_code=409, detail="Only a rejected registration can be reopened")

    stall_kept = False
    if exhibitor.get("stallId"):
        held = await db.stalls.find_one_and_update(
            {"_id": exhibitor["stallId"], "status": "available"},
            {"$set": {"status": "held", "heldBy": oid, "bookedBy": None, "tempHoldToken": None, "tempHoldExpiresAt": None,
                      "updatedAt": utcnow()}},
            return_document=True,
        )
        stall_kept = held is not None

    changes = {"status": "pending", "updatedAt": utcnow()}
    if exhibitor.get("stallId") and not stall_kept:
        changes.update({"stallNumber": "", "stallId": None, "stallRate": None})
    await db.exhibitors.update_one({"_id": oid}, {"$set": changes})

    try:
        await send_mail(
            to=exhibitor["email"],
            subject=f"Your registration has been reopened — {EVENT['eventName']}",
            html=exhibitor_reopened_email_html(exhibitor, stall_kept=stall_kept),
        )
    except Exception as mail_err:  # noqa: BLE001
        print("[exhibitor] Failed to send reopen email:", mail_err)

    updated = await db.exhibitors.find_one({"_id": oid})
    msg = "Registration reopened and the exhibitor asked to review their details"
    if exhibitor.get("stallId"):
        msg += f" — stall {exhibitor.get('stallNumber')} " + ("reserved for them again." if stall_kept else "was no longer free, so it has been cleared; assign one when approving.")
    return {"success": True, "message": msg, "data": serialize_doc(updated)}


@router.get("/exhibitors/{id}/invoice")
async def exhibitor_invoice(
    id: str,
    admin: AdminPayload = Depends(require_any_resource(["invoicing", "exhibitors"])),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    exhibitor = await db.exhibitors.find_one({"_id": oid}) if oid else None
    if not exhibitor:
        raise HTTPException(status_code=404, detail="Exhibitor not found")

    pdf_bytes = build_exhibitor_invoice_pdf(exhibitor)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=ROAR-Expo-Booking-Summary-{exhibitor['registrationCode']}.pdf"},
    )


# ---------- Stalls & Map ----------

async def _populate_holders(db: AsyncIOMotorDatabase, stalls: list[dict]) -> list[dict]:
    ids = {s[field] for s in stalls for field in ("heldBy", "bookedBy") if s.get(field)}
    if not ids:
        return stalls
    exhibitors = await db.exhibitors.find(
        {"_id": {"$in": list(ids)}}, {"companyName": 1, "contactPerson": 1, "registrationCode": 1},
    ).to_list(length=None)
    by_id = {e["_id"]: e for e in exhibitors}
    for s in stalls:
        for field in ("heldBy", "bookedBy"):
            if s.get(field) and s[field] in by_id:
                s[field] = by_id[s[field]]
    return stalls


@router.get("/stalls")
async def list_all_stalls(
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    await release_expired_holds(db)
    stalls = await db.stalls.find().sort("stallNumber", 1).to_list(length=None)
    stalls = await _populate_holders(db, stalls)
    for st in stalls:
        # A stall reserved by someone still filling in the form (no registration yet)
        st["formHold"] = bool(st.get("status") == "held" and not st.get("heldBy") and st.get("tempHoldToken"))
        st.pop("tempHoldToken", None)
    return {"success": True, "data": serialize_list(stalls)}


@router.post("/stalls")
async def create_stalls(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    stalls_in = payload.get("stalls")
    if not isinstance(stalls_in, list) or len(stalls_in) == 0:
        raise HTTPException(status_code=400, detail="Provide a non-empty 'stalls' array")

    cleaned = []
    for s in stalls_in:
        stall_number = str(s.get("stallNumber") or "").strip().upper()
        package_code = str(s.get("packageCode") or "").strip()
        try:
            rate = float(s.get("rate"))
        except (TypeError, ValueError):
            rate = float("nan")
        if not stall_number or not package_code or rate != rate or rate < 0:  # rate != rate catches NaN
            raise HTTPException(
                status_code=400,
                detail=f"Each stall needs a stallNumber, packageCode, and a valid rate (problem entry: {s})",
            )
        cleaned.append({"stallNumber": stall_number, "packageCode": package_code, "rate": rate, "size": s.get("size") or ""})

    created = []
    skipped = []
    for s in cleaned:
        existing = await db.stalls.find_one({"stallNumber": s["stallNumber"]})
        if existing:
            skipped.append(s["stallNumber"])
            continue
        doc = new_stall_document(s["stallNumber"], s["packageCode"], s["rate"], s["size"])
        result = await db.stalls.insert_one(doc)
        doc["_id"] = result.inserted_id
        created.append(doc)

    message = f"{len(created)} stall(s) added"
    if skipped:
        message += f", {len(skipped)} skipped (already existed): {', '.join(skipped)}"
    return {"success": True, "message": message, "data": serialize_list(created)}


@router.patch("/stalls/{id}")
async def update_stall(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    stall = await db.stalls.find_one({"_id": oid}) if oid else None
    if not stall:
        raise HTTPException(status_code=404, detail="Stall not found")

    updates = {}
    if "rate" in payload and payload["rate"] is not None:
        updates["rate"] = float(payload["rate"])
    if "packageCode" in payload and payload["packageCode"] is not None:
        updates["packageCode"] = payload["packageCode"]
    if "size" in payload and payload["size"] is not None:
        updates["size"] = payload["size"]

    if "mapX" in payload:
        if payload["mapX"] is None:
            updates["mapX"] = None
        else:
            n = float(payload["mapX"])
            if n != n or n < 0 or n > 100:
                raise HTTPException(status_code=400, detail="mapX must be a number between 0 and 100")
            updates["mapX"] = n
    if "mapY" in payload:
        if payload["mapY"] is None:
            updates["mapY"] = None
        else:
            n = float(payload["mapY"])
            if n != n or n < 0 or n > 100:
                raise HTTPException(status_code=400, detail="mapY must be a number between 0 and 100")
            updates["mapY"] = n

    if "status" in payload and payload["status"] is not None:
        status = payload["status"]
        if status not in STALL_STATUS_VALUES:
            raise HTTPException(status_code=400, detail="Invalid status")
        updates["status"] = status
        if status == "available":
            updates["heldBy"] = None
            updates["bookedBy"] = None

    if updates:
        updates["updatedAt"] = utcnow()
        await db.stalls.update_one({"_id": oid}, {"$set": updates})

    updated = await db.stalls.find_one({"_id": oid})
    return {"success": True, "data": serialize_doc(updated)}


@router.delete("/stalls/{id}")
async def delete_stall(
    id: str, admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    stall = await db.stalls.find_one({"_id": oid}) if oid else None
    if not stall:
        raise HTTPException(status_code=404, detail="Stall not found")
    if stall["status"] == "booked":
        raise HTTPException(status_code=409, detail="Cannot delete a booked stall — change its status first")
    await db.stalls.delete_one({"_id": oid})
    return {"success": True, "message": "Stall removed"}


# Upload the venue layout as an image or a PDF (first page rendered to PNG).
# An optional `series` form field (JSON array of {prefix, packageCode,
# separator}) records which letter series on the drawing belongs to which
# category; when omitted the previous map's mapping is carried forward so
# re-uploading a corrected drawing doesn't wipe it.
@router.post("/stalls/upload-map")
async def upload_stall_map(
    map: UploadFile = File(...), series: str | None = Form(None),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    parsed_series, err = parse_series(series)
    if err:
        raise HTTPException(status_code=400, detail=err)

    contents = await read_upload(
        map, MAP_TYPES, STALL_MAP_MAX_BYTES, "Only PNG, JPG, WEBP images or a PDF are allowed for the layout",
    )
    is_pdf = map.content_type == "application/pdf"
    if is_pdf:
        try:
            contents = await asyncio.to_thread(pdf_first_page_to_png, contents)
        except Exception as conv_err:  # noqa: BLE001
            print("[stalls] PDF conversion failed:", conv_err)
            raise HTTPException(
                status_code=400,
                detail=f"Couldn't render the PDF: {conv_err}. Try exporting the layout as a PNG/JPG and uploading that.",
            )
    filename = write_upload_bytes(contents, "stall-maps", map.filename or "layout", force_ext=".png" if is_pdf else None)
    url = f"/uploads/stall-maps/{filename}"

    previous = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    doc = new_stall_map_document(
        filename, url, source_type="pdf" if is_pdf else "image", original_filename=map.filename or "",
        series=parsed_series if parsed_series is not None else (previous or {}).get("series") or [],
    )
    result = await db.stall_maps.insert_one(doc)
    doc["_id"] = result.inserted_id

    # Detect the stalls drawn on the layout in the background — reading a
    # hundred labels takes 20–60 s depending on the server, longer than some
    # proxies allow a single request — and hand back immediately. The
    # dashboard polls GET /stalls/detection until it's done, then opens the
    # one-time confirmation so the admin can apply everything.
    await _start_detection(db, doc["_id"], contents)
    return {
        "success": True,
        "message": "PDF layout converted and uploaded" if is_pdf else "Stall map uploaded",
        "data": {**map_payload(doc), "detection": {"status": "running"}},
    }


def _detection_view(stall_map: dict | None) -> dict:
    """What the dashboard sees for the current map's detection job."""
    det = (stall_map or {}).get("detection") or {}
    if not det:
        return {"status": "none"}
    view = {"status": det.get("status", "none"), "applied": bool(det.get("applied")), "error": det.get("error") or ""}
    if det.get("status") == "done":
        view.update({k: det.get(k) for k in ("boxes", "rows", "prefixes", "ocrEngine", "imageWidth", "imageHeight")})
        view["ok"] = True
    return view


async def _run_detection(image_bytes: bytes) -> dict:
    try:
        det = await asyncio.to_thread(detect_layout, image_bytes)
    except Exception as err:  # noqa: BLE001 — detection is best-effort; manual placement still works
        print("[stalls] layout detection failed:", err)
        return {"ok": False, "error": _friendly_detection_error(err), "boxes": [], "rows": [], "prefixes": [], "ocrEngine": None}
    for p in det["prefixes"]:
        p["suggestedPackageCode"] = suggest_package_for_prefix(p["prefix"], EVENT["stallPackages"])
    det["ok"] = True
    return det


def _friendly_detection_error(err: Exception) -> str:
    text = str(err)
    if "cv2" in text or "opencv" in text.lower() or "numpy" in text.lower():
        return (
            "The server is missing the image libraries needed for automatic detection "
            "(opencv-python-headless, numpy). Install the packages in backend_fastapi/requirements.txt "
            "and redeploy, or place stalls by hand below."
        )
    return text or "Detection failed"


async def _start_detection(db: AsyncIOMotorDatabase, map_id, image_bytes: bytes) -> None:
    await db.stall_maps.update_one(
        {"_id": map_id},
        {"$set": {"detection": {"status": "running", "startedAt": utcnow(), "applied": False}}},
    )

    async def job():
        det = await _run_detection(image_bytes)
        if det.get("ok"):
            stored = {"status": "done", "finishedAt": utcnow(), "applied": False, **{k: det[k] for k in ("boxes", "rows", "prefixes", "ocrEngine", "imageWidth", "imageHeight")}}
        else:
            stored = {"status": "error", "finishedAt": utcnow(), "applied": False, "error": det.get("error") or "Detection failed"}
        try:
            await db.stall_maps.update_one({"_id": map_id}, {"$set": {"detection": stored}})
        except Exception as save_err:  # noqa: BLE001
            print("[stalls] could not store detection result:", save_err)

    asyncio.create_task(job())


# Poll the background detection job for the current layout.
@router.get("/stalls/detection")
async def get_detection(
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    current = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not current:
        return {"success": True, "data": {"status": "none"}}
    view = _detection_view(current)
    # A job that never finished (server restarted mid-run) shouldn't spin forever.
    started = (current.get("detection") or {}).get("startedAt")
    if started is not None and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)  # Mongo hands back naive UTC
    if view["status"] == "running" and started and (utcnow() - started).total_seconds() > 600:
        view = {"status": "error", "error": "Detection timed out — click “Detect stalls on this layout” to try again.", "applied": False}
    return {"success": True, "data": {**map_payload(current), "detection": view}}


# Re-run stall detection on the current layout (for maps uploaded before
# this feature existed, or to try again after fixing the drawing).
@router.post("/stalls/detect-layout")
async def detect_current_layout(
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    current = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not current:
        raise HTTPException(status_code=404, detail="Upload a layout first")
    filename = current.get("filename") or (current.get("url") or "").rsplit("/", 1)[-1]
    if not filename:
        raise HTTPException(status_code=404, detail="The layout file is missing — upload it again")
    try:
        image_bytes, _ = await asyncio.to_thread(get_object, f"roar-expo/stall-maps/{filename}")
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="The layout file is missing — upload it again")
    await _start_detection(db, current["_id"], image_bytes)
    return {"success": True, "data": {**map_payload(current), "detection": {"status": "running"}}}


# One-click: publish the FINAL venue drawing bundled with the app
# (seed/assets/final-layout.png) together with every stall on it — the same
# thing `python -m seed.final_layout_seed` does, for hosts where the admin
# can't open a shell.
@router.post("/stalls/apply-bundled-layout")
async def apply_bundled_layout(
    payload: dict | None = Body(None),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    from seed.final_layout import apply_final_layout
    keep_old = bool((payload or {}).get("keepOld"))
    try:
        result = await apply_final_layout(db, replace_unplaced=not keep_old)
    except FileNotFoundError as err:
        raise HTTPException(status_code=500, detail=str(err))
    return {
        "success": True,
        "message": (
            f"Final layout published — {len(result['created'])} stall(s) created, {len(result['updated'])} refreshed"
            + (f", {len(result['removed'])} old sample stall(s) removed" if result["removed"] else "")
            + f". {result['total']} stalls are now on the map."
        ),
        "data": result,
    }


# Apply a confirmed layout: saves the series → category mapping and creates
# or updates every listed stall WITH its map position, so markers appear on
# the registration page and the public Stalls page immediately.
@router.post("/stalls/apply-layout")
async def apply_layout(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    current = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not current:
        raise HTTPException(status_code=404, detail="Upload a layout first")

    parsed_series, err = parse_series(payload.get("series") or [])
    if err:
        raise HTTPException(status_code=400, detail=err)

    stalls_in = payload.get("stalls")
    if not isinstance(stalls_in, list) or not stalls_in:
        raise HTTPException(status_code=400, detail="No stalls to apply")

    created, updated, seen = [], [], set()
    for s in stalls_in:
        number = str(s.get("stallNumber") or "").strip().upper()
        code = str(s.get("packageCode") or "").strip()
        pkg = find_stall_package(code)
        try:
            map_x, map_y = float(s.get("mapX")), float(s.get("mapY"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Stall {number or '?'} has no map position")
        if not number or not pkg:
            raise HTTPException(status_code=400, detail=f"Stall {number or '?'} needs a number and a valid category")
        if number in seen:
            raise HTTPException(status_code=400, detail=f"Stall number {number} appears more than once")
        seen.add(number)
        map_x, map_y = max(0.0, min(100.0, map_x)), max(0.0, min(100.0, map_y))

        existing = await db.stalls.find_one({"stallNumber": number})
        if existing:
            await db.stalls.update_one(
                {"_id": existing["_id"]},
                {"$set": {"packageCode": code, "size": pkg["label"], "mapX": map_x, "mapY": map_y, "updatedAt": utcnow()}},
            )
            updated.append(number)
        else:
            doc = new_stall_document(number, code, pkg.get("rate") or 0, pkg["label"])
            doc["mapX"], doc["mapY"] = map_x, map_y
            await db.stalls.insert_one(doc)
            created.append(number)

    await db.stall_maps.update_one(
        {"_id": current["_id"]},
        {"$set": {"series": parsed_series or [], "detection.applied": True, "updatedAt": utcnow()}},
    )
    return {
        "success": True,
        "message": f"Layout applied — {len(created)} stall(s) created, {len(updated)} updated with their positions",
        "data": {"created": created, "updated": updated},
    }


# Save/replace the series → category mapping on the current map.
@router.put("/stalls/map-series")
async def update_map_series(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    current = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not current:
        raise HTTPException(status_code=404, detail="Upload a layout first")
    parsed_series, err = parse_series(payload.get("series") if "series" in payload else [])
    if err:
        raise HTTPException(status_code=400, detail=err)
    await db.stall_maps.update_one({"_id": current["_id"]}, {"$set": {"series": parsed_series or [], "updatedAt": utcnow()}})
    updated = await db.stall_maps.find_one({"_id": current["_id"]})
    return {"success": True, "message": "Layout series saved", "data": map_payload(updated)}


# Creates the stall records implied by the layout's series mapping: for each
# series, prefix+separator+1 … up to that category's stallCount on the rate
# card (or an explicit counts[prefix] override), at the category's rate.
# Existing stall numbers are left untouched.
@router.post("/stalls/generate-from-series")
async def generate_stalls_from_series(
    payload: dict = Body(default={}),
    admin: AdminPayload = Depends(require_resource("stall-inventory")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    current = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not current or not current.get("series"):
        raise HTTPException(status_code=400, detail="Save the series → category mapping first")
    counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
    created, skipped = [], []
    for s in current["series"]:
        pkg = find_stall_package(s["packageCode"])
        if not pkg:
            continue
        try:
            override = int(counts.get(s["prefix"]) or 0)
        except (TypeError, ValueError):
            override = 0
        count = override if override > 0 else (pkg.get("stallCount") or 0)
        for i in range(1, count + 1):
            stall_number = f"{s['prefix']}{s.get('separator') or ''}{i}".upper()
            if await db.stalls.find_one({"stallNumber": stall_number}):
                skipped.append(stall_number)
                continue
            await db.stalls.insert_one(new_stall_document(stall_number, s["packageCode"], pkg.get("rate") or 0, pkg["label"]))
            created.append(stall_number)
    message = f"{len(created)} stall(s) created" + (f", {len(skipped)} already existed" if skipped else "")
    return {"success": True, "message": message, "data": {"created": created, "skipped": skipped}}


# ---------- Visitors ----------

@router.get("/visitors")
async def list_visitors(
    search: str = "", page: int = 1, limit: int = 25,
    admin: AdminPayload = Depends(require_resource("visitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = _search_query(search, ["fullName", "email", "phone", "registrationCode", "organization"])
    skip = (page - 1) * limit
    total = await db.visitors.count_documents(query)
    items = await db.visitors.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(length=None)
    return {"success": True, "data": serialize_list(items), "total": total, "page": page, "limit": limit}


@router.get("/visitors/export")
async def export_visitors_csv(
    admin: AdminPayload = Depends(require_resource("visitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    items = await db.visitors.find().sort("createdAt", -1).to_list(length=None)
    csv_text = _to_csv(items, VISITOR_CSV_COLUMNS)
    return Response(
        content=csv_text, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=visitors.csv"},
    )


# Returns a QR code (as a data URL) encoding the public visitor registration
# link, tagged with ?source=onsite so walk-in registrations made from the
# poster are distinguishable from ones made ahead of time. Print this and
# display it at the main entrance.
@router.get("/visitors/entrance-qr")
async def entrance_qr(admin: AdminPayload = Depends(require_resource("visitors"))):
    base = (os.environ.get("PUBLIC_SITE_URL") or "").rstrip("/")
    url = f"{base}/register/visitor?source=onsite"

    qr_img = qrcode.make(url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

    return {"success": True, "data": {"url": url, "qrDataUrl": qr_data_url}}


# Fields an admin may edit on a visitor registration. Deliberately excludes
# registrationCode (it's printed on the visitor's QR/ID card) and the
# email/WhatsApp delivery flags.
EDITABLE_VISITOR_FIELDS = [
    "fullName", "email", "phone", "city", "organization", "designation",
    "interests", "howDidYouHear", "numberOfGuests", "source", "checkedIn",
]


# One visitor registration in full — the admin record page.
@router.get("/visitors/{id}")
async def get_visitor(
    id: str, admin: AdminPayload = Depends(require_resource("visitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    visitor = await db.visitors.find_one({"_id": oid}) if oid else None
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return {"success": True, "data": serialize_doc(visitor)}


@router.patch("/visitors/{id}")
async def edit_visitor(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("visitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    visitor = await db.visitors.find_one({"_id": oid}) if oid else None
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    updates = {}
    for field in EDITABLE_VISITOR_FIELDS:
        if field not in payload or payload[field] is None:
            continue
        value = payload[field]
        if field == "numberOfGuests":
            try:
                n = int(value)
            except (TypeError, ValueError):
                n = -1
            if n < 1 or n > 10:
                raise HTTPException(status_code=400, detail="Guests must be between 1 and 10")
            updates["numberOfGuests"] = n
        elif field == "source":
            if value not in ("online", "onsite"):
                raise HTTPException(status_code=400, detail="source must be 'online' or 'onsite'")
            updates["source"] = value
        elif field == "checkedIn":
            flag = value is True or value == "true"
            updates["checkedIn"] = flag
            updates["checkedInAt"] = (visitor.get("checkedInAt") or utcnow()) if flag else None
        elif field == "interests":
            updates["interests"] = value if isinstance(value, list) else []
        elif field == "email":
            updates["email"] = str(value).strip().lower()
        else:
            updates[field] = str(value).strip()

    if updates:
        updates["updatedAt"] = utcnow()
        await db.visitors.update_one({"_id": oid}, {"$set": updates})

    updated = await db.visitors.find_one({"_id": oid})
    return {"success": True, "message": "Visitor updated", "data": serialize_doc(updated)}


@router.delete("/visitors/{id}")
async def delete_visitor(
    id: str, admin: AdminPayload = Depends(require_resource("visitors")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    visitor = await db.visitors.find_one({"_id": oid}) if oid else None
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    await db.visitors.delete_one({"_id": oid})
    return {"success": True, "message": "Visitor registration deleted"}


@router.post("/check-in")
async def check_in_visitor(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_any_resource(["visitors", "scanning"])),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    registration_code = payload.get("registrationCode")
    if not registration_code:
        raise HTTPException(status_code=400, detail="registrationCode is required")

    visitor = await db.visitors.find_one({"registrationCode": registration_code.strip().upper()})
    if not visitor:
        raise HTTPException(status_code=404, detail="Registration code not found")

    if visitor.get("checkedIn"):
        return {"success": True, "message": "Already checked in", "data": serialize_doc(visitor), "alreadyCheckedIn": True}

    now = utcnow()
    await db.visitors.update_one({"_id": visitor["_id"]}, {"$set": {"checkedIn": True, "checkedInAt": now}})
    visitor["checkedIn"] = True
    visitor["checkedInAt"] = now
    return {"success": True, "message": "Checked in successfully", "data": serialize_doc(visitor)}


# ---------- Enquiries (public Enquiry page) — "all" or "enquiries" ----------

@router.get("/enquiries")
async def list_enquiries(
    search: str = "", page: int = 1, limit: int = 25, status: str | None = None,
    admin: AdminPayload = Depends(require_resource("enquiries")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = _search_query(search, ["name", "email", "mobile", "details"])
    if status in ENQUIRY_STATUS_VALUES:
        query["status"] = status
    skip = (page - 1) * limit
    total = await db.enquiries.count_documents(query)
    new_count = await db.enquiries.count_documents({"status": "new"})
    items = await db.enquiries.find(query).sort("createdAt", -1).skip(skip).limit(limit).to_list(length=None)
    return {"success": True, "data": serialize_list(items), "total": total, "newCount": new_count, "page": page, "limit": limit}


@router.get("/enquiries/export")
async def export_enquiries_csv(
    admin: AdminPayload = Depends(require_resource("enquiries")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    items = await db.enquiries.find().sort("createdAt", -1).to_list(length=None)
    return Response(
        content=_to_csv(items, ENQUIRY_CSV_COLUMNS), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enquiries.csv"},
    )


# One enquiry in full — the admin record page.
@router.get("/enquiries/{id}")
async def get_enquiry(
    id: str, admin: AdminPayload = Depends(require_resource("enquiries")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    enquiry = await db.enquiries.find_one({"_id": oid}) if oid else None
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    return {"success": True, "data": serialize_doc(enquiry)}


@router.patch("/enquiries/{id}")
async def update_enquiry(
    id: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_resource("enquiries")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Edit an enquiry's details and/or its status (new | handled)."""
    oid = to_object_id(id)
    enquiry = await db.enquiries.find_one({"_id": oid}) if oid else None
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    updates = {}
    status = payload.get("status")
    if "status" in payload:
        if status not in ENQUIRY_STATUS_VALUES:
            raise HTTPException(status_code=400, detail="status must be 'new' or 'handled'")
        if status != enquiry.get("status"):
            updates["status"] = status
            updates["handledAt"] = utcnow() if status == "handled" else None
    for field in ("name", "email", "mobile", "details"):
        if field in payload and payload[field] is not None:
            value = str(payload[field]).strip()
            updates[field] = value.lower() if field == "email" else value

    merged = {**enquiry, **updates}
    if not all(merged.get(f) for f in ("name", "email", "mobile", "details")):
        raise HTTPException(status_code=400, detail="Name, email, mobile and details are all required")

    if updates:
        updates["updatedAt"] = utcnow()
        await db.enquiries.update_one({"_id": oid}, {"$set": updates})

    updated = await db.enquiries.find_one({"_id": oid})
    message = ("Marked as handled" if status == "handled" else "Reopened") if "status" in payload else "Enquiry updated"
    return {"success": True, "message": message, "data": serialize_doc(updated)}


@router.delete("/enquiries/{id}")
async def delete_enquiry(
    id: str, admin: AdminPayload = Depends(require_resource("enquiries")), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    enquiry = await db.enquiries.find_one({"_id": oid}) if oid else None
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    await db.enquiries.delete_one({"_id": oid})
    return {"success": True, "message": "Enquiry deleted"}


# ---------- Admin user management ("all" permission only) ----------

@router.get("/admins")
async def list_admins(admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db)):
    admins = await db.admins.find({}, {"passwordHash": 0}).sort("createdAt", 1).to_list(length=None)
    return {"success": True, "data": serialize_list(admins)}


@router.post("/admins")
async def create_admin(
    payload: AdminCreateRequest,
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    invalid = [p for p in payload.permissions if p not in PERMISSIONS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission(s): {', '.join(invalid)}. Must be one of: {', '.join(PERMISSIONS)}",
        )
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    normalized_email = payload.email.lower().strip()
    existing = await db.admins.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=409, detail="An admin with this email already exists")

    # "all" implies everything else — store it on its own rather than
    # alongside redundant individual permissions.
    normalized_permissions = ["all"] if "all" in payload.permissions else list(dict.fromkeys(payload.permissions))

    now = utcnow()
    doc = {
        "name": payload.name.strip(),
        "email": normalized_email,
        "passwordHash": hash_password(payload.password),
        "permissions": normalized_permissions,
        "createdBy": to_object_id(admin.get("id")) if admin.get("id") else None,
        "createdAt": now,
        "updatedAt": now,
    }
    result = await db.admins.insert_one(doc)

    return {
        "success": True, "message": "Admin created",
        "data": {"id": str(result.inserted_id), "name": doc["name"], "email": doc["email"], "permissions": doc["permissions"]},
    }


@router.delete("/admins/{id}")
async def delete_admin(
    id: str, admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = to_object_id(id)
    target = await db.admins.find_one({"_id": oid}) if oid else None
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")

    if "all" in (target.get("permissions") or []):
        full_access_count = await db.admins.count_documents({"permissions": "all"})
        if full_access_count <= 1:
            raise HTTPException(status_code=409, detail="Cannot delete the last full-access admin account")

    await db.admins.delete_one({"_id": oid})
    return {"success": True, "message": "Admin removed"}


# ---------- WhatsApp (BhashSMS) service ----------

@router.get("/whatsapp/config")
async def whatsapp_get_config(
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    cfg = await wa.get_config(db)
    return {"success": True, "data": wa.mask_config(cfg)}


@router.put("/whatsapp/config")
async def whatsapp_save_config(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    cfg = await wa.save_config(db, payload or {})
    return {"success": True, "message": "WhatsApp settings saved.", "data": wa.mask_config(cfg)}


@router.get("/whatsapp/templates")
async def whatsapp_list_templates(
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    return {"success": True, "data": await wa.list_templates(db)}


@router.put("/whatsapp/templates/{key}")
async def whatsapp_update_template(
    key: str, payload: dict = Body(...),
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    if key not in wa.TEMPLATE_KEYS:
        raise HTTPException(status_code=404, detail="Unknown template")
    body = str((payload or {}).get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Template body cannot be empty.")
    enabled = bool((payload or {}).get("enabled", True))
    data = await wa.update_template(db, key, body, enabled)
    return {"success": True, "message": "Template saved.", "data": data}


@router.get("/whatsapp/logs")
async def whatsapp_logs(
    page: int = 1, limit: int = 30,
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    skip = max(0, (page - 1) * limit)
    total = await db.whatsapp_logs.count_documents({})
    rows = await db.whatsapp_logs.find().sort("createdAt", -1).skip(skip).limit(limit).to_list(length=limit)
    return {"success": True, "data": serialize_list(rows), "total": total}


@router.post("/whatsapp/test")
async def whatsapp_test(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    phone = str((payload or {}).get("phone") or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Enter a phone number to test.")
    text = str((payload or {}).get("text") or "").strip()
    key = str((payload or {}).get("templateKey") or "").strip()
    if not text and key:
        tmpl = await db.whatsapp_templates.find_one({"key": key})
        if tmpl:
            sample = [f"Sample {v}" if "name" in v.lower() else "TEST-123" for v in tmpl.get("variables", [])]
            text = wa.render(tmpl.get("body", ""), sample)
    if not text:
        text = "This is a test message from ROAR Business Expo Nagpur."
    result = await wa.send_custom(db, to=phone, text=text, recipient_type="test", recipient_name="Test")
    return {"success": result["sent"], "message": ("Test message sent." if result["sent"] else f"Could not send: {result.get('reason')}"), "data": result}


@router.post("/whatsapp/broadcast")
async def whatsapp_broadcast(
    payload: dict = Body(...),
    admin: AdminPayload = Depends(require_full_access), db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Send a reminder or information message to a chosen audience."""
    key = str((payload or {}).get("templateKey") or "").strip()
    audience = str((payload or {}).get("audience") or "").strip()
    custom_message = str((payload or {}).get("message") or "").strip()
    if key not in ("reminder", "info_broadcast"):
        raise HTTPException(status_code=400, detail="Broadcast supports the Reminder or Information templates.")
    if audience not in ("visitors", "exhibitors", "confirmed_exhibitors", "pending_exhibitors", "unpaid_exhibitors", "all"):
        raise HTTPException(status_code=400, detail="Choose a valid audience.")

    recipients = []  # list of (phone, name, type)
    if audience in ("visitors", "all"):
        async for v in db.visitors.find({}, {"fullName": 1, "phone": 1}):
            if v.get("phone"):
                recipients.append((v["phone"], v.get("fullName") or "there", "visitor"))
    if audience in ("exhibitors", "all"):
        async for e in db.exhibitors.find({}, {"contactPerson": 1, "phone": 1, "whatsapp": 1}):
            recipients.append((e.get("whatsapp") or e.get("phone") or "", e.get("contactPerson") or "there", "exhibitor"))
    if audience == "confirmed_exhibitors":
        async for e in db.exhibitors.find({"status": "confirmed"}, {"contactPerson": 1, "phone": 1, "whatsapp": 1}):
            recipients.append((e.get("whatsapp") or e.get("phone") or "", e.get("contactPerson") or "there", "exhibitor"))
    if audience == "pending_exhibitors":
        async for e in db.exhibitors.find({"status": "pending"}, {"contactPerson": 1, "phone": 1, "whatsapp": 1}):
            recipients.append((e.get("whatsapp") or e.get("phone") or "", e.get("contactPerson") or "there", "exhibitor"))
    if audience == "unpaid_exhibitors":
        async for e in db.exhibitors.find({"status": "confirmed", "paymentStatus": {"$ne": "paid"}}, {"contactPerson": 1, "phone": 1, "whatsapp": 1}):
            recipients.append((e.get("whatsapp") or e.get("phone") or "", e.get("contactPerson") or "there", "exhibitor"))

    recipients = [(p, n, t) for (p, n, t) in recipients if p]
    sent = failed = 0
    for phone, name, rtype in recipients:
        if key == "reminder":
            vars_ = [name, wa.event_dates_label()]
        else:
            vars_ = [name, custom_message or "We have an update about ROAR Business Expo Nagpur."]
        res = await wa.send_event(db, key, to=phone, variables=vars_, recipient_type=rtype, recipient_name=name)
        if res["sent"]:
            sent += 1
        else:
            failed += 1
    return {"success": True, "message": f"Broadcast finished: {sent} sent, {failed} failed/skipped out of {len(recipients)} recipients.", "data": {"sent": sent, "failed": failed, "total": len(recipients)}}
