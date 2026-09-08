"""
Port of utils/mailer.js. Nodemailer -> Python's stdlib `smtplib` +
`email.mime`. SMTP calls are blocking, so `send_mail()` runs the actual send
in a thread (`asyncio.to_thread`) to avoid stalling the event loop, the same
way the rest of this backend stays non-blocking.

Attachments: a list of dicts shaped like the old Nodemailer attachment
objects — {"filename": str, "content": bytes, "contentType": str,
"cid": str | None}. An attachment with a `cid` is embedded inline (for the
`<img src="cid:idcard">` reference in the visitor email template); anything
else is a regular file attachment (e.g. the PDF invitation).
"""
import os
import smtplib
import ssl
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

_smtp_config_warned = False


def _get_smtp_config():
    global _smtp_config_warned
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or 465)
    secure = (os.environ.get("SMTP_SECURE") or "true").lower() == "true"
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")

    if not user or not password:
        if not _smtp_config_warned:
            print(
                "[mailer] SMTP_HOST / SMTP_USER / SMTP_PASS not fully configured. "
                "Emails will fail until you set them in .env (see .env.example)."
            )
            _smtp_config_warned = True

    return host, port, secure, user, password


def _build_message(*, to, bcc, subject, html, attachments, from_name, from_address):
    outer = MIMEMultipart("mixed")
    outer["Subject"] = subject
    outer["From"] = f'"{from_name}" <{from_address}>'
    outer["To"] = to
    if bcc:
        outer["Bcc"] = bcc

    related = MIMEMultipart("related")
    related.attach(MIMEText(html, "html"))

    for att in attachments or []:
        if att.get("cid"):
            part = MIMEBase(*_guess_maintype_subtype(att.get("contentType")))
            part.set_payload(att["content"])
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", "inline", filename=att["filename"])
            part.add_header("Content-ID", f"<{att['cid']}>")
            related.attach(part)

    outer.attach(related)

    for att in attachments or []:
        if att.get("cid"):
            continue
        part = MIMEBase(*_guess_maintype_subtype(att.get("contentType")))
        part.set_payload(att["content"])
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=att["filename"])
        outer.attach(part)

    return outer


def _guess_maintype_subtype(content_type: str | None):
    if not content_type or "/" not in content_type:
        return "application", "octet-stream"
    main, sub = content_type.split("/", 1)
    return main, sub


def _send_sync(msg: MIMEMultipart, host: str, port: int, secure: bool, user: str, password: str, recipients: list[str]):
    if secure:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(user, password)
            server.sendmail(user, recipients, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            server.sendmail(user, recipients, msg.as_string())


async def send_mail(*, to: str, bcc: str | None = None, subject: str, html: str, attachments: list | None = None):
    host, port, secure, user, password = _get_smtp_config()
    from_name = os.environ.get("MAIL_FROM_NAME") or "ROAR Expo"

    if not user or not password:
        raise RuntimeError("SMTP is not configured (SMTP_USER / SMTP_PASS missing)")

    msg = _build_message(
        to=to, bcc=bcc, subject=subject, html=html, attachments=attachments, from_name=from_name, from_address=user
    )
    # `to`/`bcc` may be comma-separated lists (e.g. the enquiry notification
    # goes to several inboxes) — the header keeps the string as-is, the SMTP
    # envelope needs each address individually.
    recipients = [a.strip() for a in f"{to},{bcc or ''}".split(",") if a.strip()]

    await asyncio.to_thread(_send_sync, msg, host, port, secure, user, password, recipients)


async def verify_mailer() -> bool:
    host, port, secure, user, password = _get_smtp_config()
    if not user or not password:
        return False

    def _verify():
        if secure:
            with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as server:
                server.login(user, password)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
        return True

    return await asyncio.to_thread(_verify)
