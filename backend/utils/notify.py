"""Instant email alerts to the organizing team.

One place decides *who* gets alerted and *whether* alerts are on, so the
exhibitor, visitor and enquiry routes just call `notify_organizers(...)`.

Env:
  ORGANIZER_NOTIFY_EMAILS  comma-separated inboxes for all alerts
                           (falls back to ENQUIRY_NOTIFY_EMAILS, then the
                           built-in admin@/mkt@ addresses)
  ADMIN_ALERTS             "false"/"0"/"off" switches the alerts off
                           (default on)

A failed alert is logged and swallowed — it must never turn a successful
registration into an error for the person who just filled in the form.
"""
import os

from utils.mailer import send_mail

DEFAULT_RECIPIENTS = "admin@roarexpo.com,mkt@roarexpo.com"


def organizer_recipients() -> str:
    raw = (
        os.environ.get("ORGANIZER_NOTIFY_EMAILS")
        or os.environ.get("ENQUIRY_NOTIFY_EMAILS")
        or DEFAULT_RECIPIENTS
    )
    return ", ".join(e.strip() for e in raw.split(",") if e.strip())


def alerts_enabled() -> bool:
    return (os.environ.get("ADMIN_ALERTS") or "true").strip().lower() not in ("false", "0", "off", "no")


async def notify_organizers(*, subject: str, html: str, kind: str = "alert") -> bool:
    """Returns True when the alert was handed to the mail server."""
    if not alerts_enabled():
        return False
    try:
        await send_mail(to=organizer_recipients(), subject=subject, html=html)
        return True
    except Exception as err:  # noqa: BLE001
        print(f"[notify] Failed to send {kind} alert to organizers:", err)
        return False
