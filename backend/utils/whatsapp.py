"""
Port of utils/whatsapp.js — WhatsApp delivery provider plug-in point.

This project isn't wired up to a specific WhatsApp Business API account
yet. Pick one provider below, add its credentials to your .env (see
.env.example), set WHATSAPP_PROVIDER to match, and you're done — the rest
of the app (visitor registration, the ID card + QR code) already calls
send_whatsapp() and needs no other changes.

Until WHATSAPP_PROVIDER is set, send_whatsapp() safely no-ops and just logs
what it *would* have sent, so registration keeps working with email-only
delivery in the meantime.

Supported providers (set WHATSAPP_PROVIDER to one of):
  "meta"    — Meta WhatsApp Cloud API (official, developers.facebook.com)
  "twilio"  — Twilio WhatsApp API
  "gupshup" — Gupshup WhatsApp API

Pass a `media_url` to send an image (e.g. the visitor's ID card) with a
caption — used for visitor registration. Omit it to send a plain text
message — used for exhibitor registration/approval, which has no ID card
image. All three providers support both. Numbers are normalized to E.164
(see normalize_phone below).
"""
import os
import re
import httpx


def normalize_phone(raw: str) -> str:
    """Best-effort Indian-first phone normalization: strips punctuation/
    spaces, assumes a bare 10-digit number is an Indian mobile (+91), and
    otherwise trusts a leading country code (with or without a "+"). Good
    enough for this event's audience — replace with a proper phone library
    if you need broader international support."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}"


async def send_whatsapp(*, to: str, caption: str, media_url: str | None = None) -> dict:
    """Returns {"sent": bool, "reason": str | None}. Never raises — callers
    should still wrap this in try/except defensively, but a provider/network
    failure here is reported back rather than raised, so a WhatsApp hiccup
    never blocks a registration."""
    provider = (os.environ.get("WHATSAPP_PROVIDER") or "").strip().lower()

    if not provider:
        print(f'[whatsapp] Not configured (set WHATSAPP_PROVIDER in .env) — would have sent to {to}: "{caption}"')
        return {"sent": False, "reason": "not_configured"}

    phone = normalize_phone(to)

    try:
        if provider == "meta":
            return await _send_via_meta_cloud_api(phone, caption, media_url)
        if provider == "twilio":
            return await _send_via_twilio(phone, caption, media_url)
        if provider == "gupshup":
            return await _send_via_gupshup(phone, caption, media_url)
        print(f'[whatsapp] Unknown WHATSAPP_PROVIDER "{provider}" — must be "meta", "twilio", or "gupshup"')
        return {"sent": False, "reason": "unknown_provider"}
    except Exception as err:  # noqa: BLE001 — deliberately broad, mirrors the JS catch-all
        print(f"[whatsapp] send failed: {err}")
        return {"sent": False, "reason": str(err)}


# ---------- Meta WhatsApp Cloud API ----------
# Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
# Needs: WHATSAPP_META_PHONE_NUMBER_ID, WHATSAPP_META_ACCESS_TOKEN
async def _send_via_meta_cloud_api(phone: str, caption: str, media_url: str | None) -> dict:
    phone_number_id = os.environ.get("WHATSAPP_META_PHONE_NUMBER_ID")
    access_token = os.environ.get("WHATSAPP_META_ACCESS_TOKEN")
    api_version = os.environ.get("WHATSAPP_META_API_VERSION") or "v20.0"

    if not phone_number_id or not access_token:
        print("[whatsapp] Meta Cloud API selected but WHATSAPP_META_PHONE_NUMBER_ID / WHATSAPP_META_ACCESS_TOKEN are missing")
        return {"sent": False, "reason": "missing_credentials"}

    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    to = phone.lstrip("+")
    payload = (
        {"messaging_product": "whatsapp", "to": to, "type": "image", "image": {"link": media_url, "caption": caption}}
        if media_url
        else {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": caption}}
    )

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(url, headers={"Authorization": f"Bearer {access_token}"}, json=payload)

    data = _safe_json(res)
    if res.status_code >= 400:
        print("[whatsapp] Meta Cloud API error:", data)
        return {"sent": False, "reason": (data.get("error") or {}).get("message") or f"HTTP {res.status_code}"}
    return {"sent": True}


# ---------- Twilio ----------
# Docs: https://www.twilio.com/docs/whatsapp/api
# Needs: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM (e.g. "whatsapp:+14155238886")
async def _send_via_twilio(phone: str, caption: str, media_url: str | None) -> dict:
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_WHATSAPP_FROM")

    if not account_sid or not auth_token or not from_number:
        print("[whatsapp] Twilio selected but TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_FROM are missing")
        return {"sent": False, "reason": "missing_credentials"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    params = {"From": from_number, "To": f"whatsapp:{phone}", "Body": caption}
    if media_url:
        params["MediaUrl"] = media_url

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(url, data=params, auth=(account_sid, auth_token))

    data = _safe_json(res)
    if res.status_code >= 400:
        print("[whatsapp] Twilio error:", data)
        return {"sent": False, "reason": data.get("message") or f"HTTP {res.status_code}"}
    return {"sent": True}


# ---------- Gupshup ----------
# Docs: https://docs.gupshup.io/docs/send-message-using-whatsapp-api
# Needs: GUPSHUP_API_KEY, GUPSHUP_SOURCE_NUMBER, GUPSHUP_APP_NAME
async def _send_via_gupshup(phone: str, caption: str, media_url: str | None) -> dict:
    import json as _json

    api_key = os.environ.get("GUPSHUP_API_KEY")
    source_number = os.environ.get("GUPSHUP_SOURCE_NUMBER")
    app_name = os.environ.get("GUPSHUP_APP_NAME")

    if not api_key or not source_number or not app_name:
        print("[whatsapp] Gupshup selected but GUPSHUP_API_KEY / GUPSHUP_SOURCE_NUMBER / GUPSHUP_APP_NAME are missing")
        return {"sent": False, "reason": "missing_credentials"}

    url = "https://api.gupshup.io/wa/api/v1/msg"
    message = (
        {"type": "image", "originalUrl": media_url, "previewUrl": media_url, "caption": caption}
        if media_url
        else {"type": "text", "text": caption}
    )
    body = {
        "channel": "whatsapp",
        "source": source_number,
        "destination": phone.lstrip("+"),
        "src.name": app_name,
        "message": _json.dumps(message),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.post(url, data=body, headers={"apikey": api_key})

    data = _safe_json(res)
    if res.status_code >= 400 or data.get("status") == "error":
        print("[whatsapp] Gupshup error:", data)
        return {"sent": False, "reason": data.get("message") or f"HTTP {res.status_code}"}
    return {"sent": True}


def _safe_json(res: httpx.Response) -> dict:
    try:
        return res.json()
    except Exception:  # noqa: BLE001
        return {}
