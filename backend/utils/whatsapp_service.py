"""
BhashSMS WhatsApp service — DLT-approved template delivery for ROAR Expo.

Config, templates and delivery logs live in MongoDB (admin-managed via the
dashboard), mirroring the gateway setup used across the organizers' other
systems. Sending is always non-blocking: a gateway/network failure is logged
and reported back, never raised, so a registration or approval never breaks.

Legacy BhashSMS endpoint (GET):
  https://bhashsms.com/api/sendmsgutil.php?user=..&pass=..&sender=BUZWAP
      &phone=<10-digit>&text=<rendered template>&priority=wa&stype=normal
"""
import re
import httpx
from datetime import timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.event_config import EVENT
from models.common import utcnow, serialize_doc, serialize_list

CONFIG_ID = "whatsapp"

DEFAULT_CONFIG = {
    "_id": CONFIG_ID,
    "enabled": False,
    "provider": "bhashsms",
    "senderId": "BUZWAP",
    "bhashUser": "",
    "bhashPassword": "",
    "apiBaseUrl": "https://bhashsms.com/api/sendmsgutil.php",
    "priority": "wa",
    "stype": "normal",
}

# Ordered variable names per template — the trigger passes values in this
# order and the body uses {{1}}, {{2}} … matching the position (DLT format).
TEMPLATE_DEFS = [
    {
        "key": "visitor_registration",
        "label": "Visitor Registration",
        "description": "Sent to a visitor right after they register.",
        "variables": ["Visitor name", "Registration ID"],
        "body": "Afzalus Salaam {{1}}, thank you for registering as a visitor for Roar Business Expo. Your registration ID is {{2}}. Please show this ID at the entrance for a quick check-in. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "exhibitor_registration",
        "label": "Exhibitor Registration",
        "description": "Sent to an exhibitor right after they register a stall.",
        "variables": ["Contact name", "Registration ID"],
        "body": "Afzalus Salaam {{1}}, thank you for registering as an exhibitor for Roar Business Expo. Your registration ID is {{2}}. Your stall is reserved and pending approval, and we will inform you once it is confirmed. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "approval",
        "label": "Approval",
        "description": "Sent when an exhibitor's stall booking is approved.",
        "variables": ["Contact name", "Stall number", "Registration ID"],
        "body": "Afzalus Salaam {{1}}, your stall {{2}} for Roar Business Expo is confirmed. Your registration ID is {{3}}. Our team will share the next steps with you shortly. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "rejection",
        "label": "Rejection",
        "description": "Sent when an exhibitor's stall booking is rejected.",
        "variables": ["Contact name", "Registration ID"],
        "body": "Afzalus Salaam {{1}}, thank you for your interest in Roar Business Expo. We are unable to confirm your stall booking for registration ID {{2}} at this time. Please contact our team for assistance. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "payment_done",
        "label": "Payment Done",
        "description": "Sent when an exhibitor's payment is marked as paid.",
        "variables": ["Contact name", "Stall number"],
        "body": "Afzalus Salaam {{1}}, we have received your payment for stall {{2}} at Roar Business Expo. Thank you. Your booking is now fully confirmed. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "unpaid",
        "label": "Unpaid / Payment Pending",
        "description": "Sent to remind an exhibitor that payment is pending.",
        "variables": ["Contact name", "Stall number"],
        "body": "Afzalus Salaam {{1}}, this is a reminder that the payment for your stall {{2}} at Roar Business Expo is still pending. Please complete the payment to secure your booking. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "reminder",
        "label": "Event Reminder",
        "description": "General reminder that can be broadcast to visitors or exhibitors.",
        "variables": ["Name", "Event dates"],
        "body": "Afzalus Salaam {{1}}, this is a friendly reminder about Roar Business Expo on {{2}}. We look forward to welcoming you. Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
    {
        "key": "info_broadcast",
        "label": "Information Broadcast",
        "description": "A flexible message to send information to exhibitors and visitors.",
        "variables": ["Name", "Message"],
        "body": "Afzalus Salaam {{1}}, {{2}} Dawoodi Bohra Department of Economic Affairs Nagpur - Roar Business Expo",
    },
]

# Bump this when the default bodies change so ensure_templates() re-applies the
# redesign to existing databases (preview + production) on the next start-up.
TEMPLATE_BODY_VERSION = "2026-06-utility-v1"

TEMPLATE_KEYS = [t["key"] for t in TEMPLATE_DEFS]
_DEF_BY_KEY = {t["key"]: t for t in TEMPLATE_DEFS}


def normalize_phone(raw: str) -> str:
    """Return a bare digits phone for BhashSMS (India). Keeps a leading 91 if
    present, otherwise assumes a 10-digit Indian mobile."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        return digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return digits


def mask_config(cfg: dict) -> dict:
    """Config for the admin UI — never expose the stored password."""
    out = {k: v for k, v in cfg.items() if k != "bhashPassword"}
    out["hasPassword"] = bool(cfg.get("bhashPassword"))
    return out


async def get_config(db: AsyncIOMotorDatabase) -> dict:
    cfg = await db.whatsapp_config.find_one({"_id": CONFIG_ID})
    if not cfg:
        cfg = dict(DEFAULT_CONFIG)
        await db.whatsapp_config.insert_one(dict(cfg))
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


async def save_config(db: AsyncIOMotorDatabase, updates: dict) -> dict:
    current = await get_config(db)
    allowed = ("enabled", "senderId", "bhashUser", "apiBaseUrl", "priority", "stype")
    changes = {k: updates[k] for k in allowed if k in updates}
    # Only overwrite the password when a non-empty new value is supplied.
    new_pw = updates.get("bhashPassword")
    if new_pw:
        changes["bhashPassword"] = new_pw
    changes["updatedAt"] = utcnow()
    await db.whatsapp_config.update_one({"_id": CONFIG_ID}, {"$set": changes}, upsert=True)
    return await get_config(db)


async def ensure_templates(db: AsyncIOMotorDatabase) -> None:
    """Seed missing default templates, and re-apply the default bodies/labels
    whenever TEMPLATE_BODY_VERSION changes (keeps each template's DLT name and
    enabled flag)."""
    for t in TEMPLATE_DEFS:
        existing = await db.whatsapp_templates.find_one({"key": t["key"]})
        if not existing:
            await db.whatsapp_templates.insert_one({
                "key": t["key"], "label": t["label"], "description": t["description"],
                "variables": t["variables"], "body": t["body"], "templateName": t.get("templateName", ""),
                "enabled": True, "bodyVersion": TEMPLATE_BODY_VERSION,
                "createdAt": utcnow(), "updatedAt": utcnow(),
            })
        elif existing.get("bodyVersion") != TEMPLATE_BODY_VERSION:
            await db.whatsapp_templates.update_one(
                {"key": t["key"]},
                {"$set": {"label": t["label"], "description": t["description"],
                          "variables": t["variables"], "body": t["body"],
                          "bodyVersion": TEMPLATE_BODY_VERSION,
                          "templateName": existing.get("templateName", ""),
                          "updatedAt": utcnow()}},
            )


async def list_templates(db: AsyncIOMotorDatabase) -> list:
    await ensure_templates(db)
    rows = await db.whatsapp_templates.find().to_list(length=None)
    # Preserve the canonical order.
    rows.sort(key=lambda r: TEMPLATE_KEYS.index(r["key"]) if r["key"] in TEMPLATE_KEYS else 99)
    return serialize_list(rows)


async def update_template(db: AsyncIOMotorDatabase, key: str, body: str, enabled: bool,
                          template_name: str | None = None) -> dict:
    await ensure_templates(db)
    changes = {"body": body, "enabled": bool(enabled), "updatedAt": utcnow()}
    if template_name is not None:
        changes["templateName"] = template_name.strip()
    await db.whatsapp_templates.update_one({"key": key}, {"$set": changes})
    return serialize_doc(await db.whatsapp_templates.find_one({"key": key}))


def render(body: str, variables: list) -> str:
    """Substitute {{1}}, {{2}} … with the given values; strip newlines (DLT
    templates must not contain \\n)."""
    text = body or ""
    for i, val in enumerate(variables or [], start=1):
        text = text.replace("{{%d}}" % i, str(val if val is not None else ""))
    return re.sub(r"\s*\n\s*", " ", text).strip()


async def _log(db, *, to, template_key, text, status, reason, provider_response,
               recipient_type=None, recipient_name=None):
    await db.whatsapp_logs.insert_one({
        "to": to, "templateKey": template_key, "text": text, "status": status,
        "reason": reason or "", "providerResponse": provider_response or "",
        "recipientType": recipient_type or "", "recipientName": recipient_name or "",
        "createdAt": utcnow(),
    })


async def _send_bhash(cfg: dict, phone: str, text: str, media_url: str | None,
                      params_list: list | None = None) -> dict:
    """Fire the BhashSMS legacy GET request. `text` is either the full message
    (plain mode) or the DLT template name (template mode); in template mode the
    variable values are passed comma-separated in `Params`. Returns {sent, reason, raw}."""
    if not cfg.get("bhashUser") or not cfg.get("bhashPassword"):
        return {"sent": False, "reason": "missing_credentials", "raw": ""}
    params = {
        "user": cfg["bhashUser"], "pass": cfg["bhashPassword"], "sender": cfg.get("senderId") or "BUZWAP",
        "phone": phone, "text": text, "priority": cfg.get("priority") or "wa",
        "stype": cfg.get("stype") or "normal",
    }
    if params_list:
        # BhashSMS DLT WhatsApp: variable values, comma-separated, in order.
        params["Params"] = ",".join(str(v).replace(",", " ") for v in params_list)
    if media_url:
        params["htype"] = "image"
        params["url"] = media_url
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            res = await client.get(cfg.get("apiBaseUrl") or DEFAULT_CONFIG["apiBaseUrl"], params=params)
        raw = (res.text or "").strip()
        low = raw.lower()
        # BhashSMS signals success with a response beginning "S." (+ message id).
        # Anything else (e.g. "Only Utility ... Templates Supported", credit or
        # auth errors) is a failure even though it returns HTTP 200.
        ok = res.status_code < 400 and (
            raw.upper().startswith("S.") or "success" in low or raw.isdigit()
        )
        if not ok:
            return {"sent": False, "reason": raw or f"HTTP {res.status_code}", "raw": raw}
        return {"sent": True, "reason": None, "raw": raw}
    except Exception as err:  # noqa: BLE001
        return {"sent": False, "reason": str(err), "raw": ""}


async def send_event(db: AsyncIOMotorDatabase, key: str, *, to: str, variables: list,
                     recipient_type: str | None = None, recipient_name: str | None = None,
                     media_url: str | None = None) -> dict:
    """Render a template by key and deliver it via BhashSMS, recording a log.
    Non-blocking and safe: returns {"sent": bool, "reason": str|None}."""
    cfg = await get_config(db)
    phone = normalize_phone(to)
    if not phone:
        return {"sent": False, "reason": "no_phone"}

    tmpl = await db.whatsapp_templates.find_one({"key": key})
    if not tmpl:
        await ensure_templates(db)
        tmpl = await db.whatsapp_templates.find_one({"key": key})
    if not tmpl:
        return {"sent": False, "reason": "template_missing"}

    text = render(tmpl.get("body", ""), variables)
    tmpl_name = (tmpl.get("templateName") or "").strip()

    if not cfg.get("enabled"):
        await _log(db, to=phone, template_key=key, text=text, status="skipped",
                   reason="whatsapp_disabled", provider_response="",
                   recipient_type=recipient_type, recipient_name=recipient_name)
        return {"sent": False, "reason": "whatsapp_disabled"}
    if not tmpl.get("enabled", True):
        await _log(db, to=phone, template_key=key, text=text, status="skipped",
                   reason="template_disabled", provider_response="",
                   recipient_type=recipient_type, recipient_name=recipient_name)
        return {"sent": False, "reason": "template_disabled"}

    # DLT template mode: send the approved template NAME + variable values.
    # Plain mode (no template name set yet): send the rendered message text.
    if tmpl_name:
        result = await _send_bhash(cfg, phone, tmpl_name, media_url, params_list=[str(v) for v in (variables or [])])
    else:
        result = await _send_bhash(cfg, phone, text, media_url)
    await _log(db, to=phone, template_key=key, text=text,
               status="sent" if result["sent"] else "failed",
               reason=result.get("reason"), provider_response=result.get("raw"),
               recipient_type=recipient_type, recipient_name=recipient_name)
    return {"sent": result["sent"], "reason": result.get("reason")}


async def send_custom(db: AsyncIOMotorDatabase, *, to: str, text: str,
                      recipient_type: str | None = None, recipient_name: str | None = None,
                      media_url: str | None = None) -> dict:
    """Send an already-rendered message (used by the test button)."""
    cfg = await get_config(db)
    phone = normalize_phone(to)
    clean = re.sub(r"\s*\n\s*", " ", text or "").strip()
    if not cfg.get("enabled"):
        await _log(db, to=phone, template_key="test", text=clean, status="skipped",
                   reason="whatsapp_disabled", provider_response="",
                   recipient_type=recipient_type, recipient_name=recipient_name)
        return {"sent": False, "reason": "whatsapp_disabled"}
    result = await _send_bhash(cfg, phone, clean, media_url)
    await _log(db, to=phone, template_key="test", text=clean,
               status="sent" if result["sent"] else "failed",
               reason=result.get("reason"), provider_response=result.get("raw"),
               recipient_type=recipient_type, recipient_name=recipient_name)
    return {"sent": result["sent"], "reason": result.get("reason")}


def event_dates_label() -> str:
    return EVENT.get("eventDatesLabel") or EVENT.get("eventDates") or ""
