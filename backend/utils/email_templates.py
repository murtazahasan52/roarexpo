"""Port of utils/emailTemplates.js — plain f-string HTML, same markup/inline
styles as the original so the emails render identically."""
from config.event_config import EVENT, find_stall_package

_BRAND_HEADER = f"""
  <div style="background:#0c1a33;padding:24px 32px;text-align:center;">
    <div style="font-family:Georgia,'Times New Roman',serif;font-size:34px;font-weight:bold;letter-spacing:6px;color:#f2a93b;">
      ROAR
    </div>
    <div style="font-family:Arial,sans-serif;font-size:13px;letter-spacing:2px;color:#ffffff;text-transform:uppercase;margin-top:4px;">
      Business Expo &mdash; {EVENT['eventCity']}
    </div>
  </div>
"""

_BRAND_FOOTER = f"""
  <div style="background:#f4f5f7;padding:20px 32px;text-align:center;font-family:Arial,sans-serif;font-size:12px;color:#666;">
    <p style="margin:0 0 6px;">{EVENT['venueName']} &middot; {EVENT['eventDatesLabel']}</p>
    <p style="margin:0 0 6px;">Questions? WhatsApp us at {EVENT['contact']['whatsapp']} (message only &mdash; no calls) or email
      <a href="mailto:{EVENT['contact']['email']}" style="color:#0c1a33;">{EVENT['contact']['email']}</a>
    </p>
    <p style="margin:0;color:#999;">A stronger business community, for a brighter tomorrow.</p>
  </div>
"""


import os

# Title-sponsor bank account for stall payments (from the organizer's cheque).
_PAYMENT = {
    "bankName": "Axis Bank Ltd",
    "branch": "Lakadganj, Nagpur (MH) — 440008",
    "accountName": "Dawoodi Bohra Jamaat Trust",
    "accountNumber": "330010200004312",
    "ifsc": "UTIB0000330",
}

_CHEQUE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "payment-cheque.jpg")


def payment_cheque_attachments() -> list:
    """Inline cheque image (cid:cheque) for the payment emails; [] if missing."""
    try:
        with open(_CHEQUE_PATH, "rb") as f:
            return [{"filename": "account-cheque.jpg", "content": f.read(),
                     "contentType": "image/jpeg", "cid": "cheque"}]
    except OSError:
        return []


def _payment_section(exhibitor: dict, *, reminder: bool = False) -> str:
    rate = exhibitor.get("stallRate")
    n = exhibitor.get("numberOfStalls") or 1
    total = exhibitor.get("totalAmount")
    try:
        total = int(total) if total is not None else (int(rate) * int(n) if rate is not None else None)
    except (TypeError, ValueError):
        total = None
    amount_html = ""
    if total is not None:
        try:
            per = f"₹{int(rate):,} × {n} stall(s)" if rate is not None and int(n) > 1 else f"₹{int(rate):,}"
        except (TypeError, ValueError):
            per = None
        detail = f' <span style="font-weight:normal;color:#888;">({per})</span>' if per else ""
        amount_html = (
            f'<tr><td style="padding:6px 0;color:#666;width:180px;">Amount Payable</td>'
            f'<td style="padding:6px 0;font-weight:bold;color:#0c1a33;">₹{total:,}{detail}</td></tr>'
        )
    heading = "Payment Reminder" if reminder else "Payment Details — Transfer Your Stall Amount"
    intro = (
        "This is a gentle reminder to complete the payment for your stall booking. "
        "Please transfer the amount to the account below and share the payment receipt with us."
        if reminder else
        "To secure your stall, please transfer the amount to the account below and share the payment receipt with us."
    )
    return f"""
    <div style="margin:22px 0;padding:18px 20px;background:#fbf7ee;border:1px solid #ecdfbf;border-radius:10px;">
      <h3 style="margin:0 0 8px;color:#0c1a33;">{heading}</h3>
      <p style="margin:0 0 12px;color:#444;">{intro}</p>
      <table style="width:100%;border-collapse:collapse;">
        {amount_html}
        <tr><td style="padding:6px 0;color:#666;width:180px;">Account Name</td><td style="padding:6px 0;font-weight:bold;">{_PAYMENT['accountName']}</td></tr>
        <tr><td style="padding:6px 0;color:#666;">Bank</td><td style="padding:6px 0;">{_PAYMENT['bankName']}</td></tr>
        <tr><td style="padding:6px 0;color:#666;">Branch</td><td style="padding:6px 0;">{_PAYMENT['branch']}</td></tr>
        <tr><td style="padding:6px 0;color:#666;">Account Number</td><td style="padding:6px 0;font-weight:bold;letter-spacing:1px;">{_PAYMENT['accountNumber']}</td></tr>
        <tr><td style="padding:6px 0;color:#666;">IFSC Code</td><td style="padding:6px 0;font-weight:bold;">{_PAYMENT['ifsc']}</td></tr>
      </table>
      <p style="margin:14px 0 8px;color:#666;font-size:13px;">Cheque copy for your reference:</p>
      <div style="text-align:center;">
        <img src="cid:cheque" alt="Bank account cheque for stall payment" style="width:100%;max-width:460px;border:1px solid #e3d9c0;border-radius:8px;" />
      </div>
      <p style="margin:12px 0 0;color:#888;font-size:12px;">After transferring, please reply with the transaction reference / screenshot so we can mark your payment as received.</p>
    </div>
  """


def _wrap(inner_html: str) -> str:
    return f"""
  <div style="max-width:600px;margin:0 auto;font-family:Arial,sans-serif;color:#222;border:1px solid #eee;">
    {_BRAND_HEADER}
    <div style="padding:28px 32px;">
      {inner_html}
    </div>
    {_BRAND_FOOTER}
  </div>
  """


def exhibitor_email_html(exhibitor: dict) -> str:
    pkg = find_stall_package(exhibitor.get("stallPackage"))
    inst = EVENT["exhibitorInstructions"]

    docs_list = "".join(f'<li style="margin-bottom:6px;">{d}</li>' for d in inst["documentsRequired"])
    guide_list = "".join(f'<li style="margin-bottom:6px;">{g}</li>' for g in inst["guidelines"])

    stall_rate = exhibitor.get("stallRate")
    stall_rows = (
        f"""
      <tr><td style="padding:6px 0;color:#666;">Stall Number</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get('stallNumber')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Stall Rate</td><td style="padding:6px 0;">{f"₹{stall_rate}" if stall_rate is not None else "To be confirmed"}</td></tr>
    """
        if exhibitor.get("stallNumber")
        else ""
    )

    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">Your stall registration has been received!</h2>
    <p>Dear {exhibitor.get('contactPerson')},</p>
    <p>Thank you for registering <strong>{exhibitor.get('companyName')}</strong> as an exhibitor at
      <strong>{EVENT['eventName']}</strong>. Your registration{" and stall reservation" if exhibitor.get('stallNumber') else ""}
      is now <strong>pending organizer approval</strong> &mdash; we'll confirm it shortly. Here are your
      registration details and everything you need to prepare for the expo.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:180px;">Registration ID</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get('registrationCode')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">ITS Number</td><td style="padding:6px 0;">{exhibitor.get('itsNumber') or "—"}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Category</td><td style="padding:6px 0;">{exhibitor.get('category')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Stall Package</td><td style="padding:6px 0;">{pkg['label'] if pkg else exhibitor.get('stallPackage')}</td></tr>
      {stall_rows}
      <tr><td style="padding:6px 0;color:#666;">Number of Stalls</td><td style="padding:6px 0;">{exhibitor.get('numberOfStalls')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Event Dates</td><td style="padding:6px 0;">{EVENT['eventDatesLabel']}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Venue</td><td style="padding:6px 0;">{EVENT['venueName']}</td></tr>
    </table>

    <h3 style="color:#0c1a33;margin-bottom:6px;">Move-in &amp; Move-out Schedule</h3>
    <p style="margin-top:0;">Setup window: <strong>{inst['setupWindow']}</strong><br/>
      Daily show timing: <strong>{inst['dailyShowTiming']}</strong><br/>
      Move-out window: <strong>{inst['moveOutWindow']}</strong></p>

    <h3 style="color:#0c1a33;margin-bottom:6px;">Documents to Bring</h3>
    <ul style="margin-top:0;padding-left:20px;">{docs_list}</ul>

    <h3 style="color:#0c1a33;margin-bottom:6px;">Exhibitor Guidelines</h3>
    <ul style="margin-top:0;padding-left:20px;">{guide_list}</ul>

    <h3 style="color:#0c1a33;margin-bottom:6px;">Registration Deadline &amp; Cancellation</h3>
    <p style="margin-top:0;">Final registration/payment deadline: <strong>{EVENT['registrationDeadlines']['stall']}</strong>.<br/>
      {inst['cancellationPolicy']}</p>

    <p>Our team will review and confirm your stall shortly. For any queries, reply to this email or
      WhatsApp us at <strong>{EVENT['contact']['whatsapp']}</strong> (message only &mdash; no calls).</p>

    {_payment_section(exhibitor)}

    <p style="margin-bottom:0;">We look forward to a great show together!<br/>Team ROAR Expo</p>
  """

    return _wrap(inner)


def exhibitor_approved_email_html(exhibitor: dict) -> str:
    stall_row = (
        f'<tr><td style="padding:6px 0;color:#666;">Stall Number</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get("stallNumber")}</td></tr>'
        if exhibitor.get("stallNumber")
        else ""
    )
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">You're confirmed! 🎉</h2>
    <p>Dear {exhibitor.get('contactPerson')},</p>
    <p>Great news &mdash; your stall registration for <strong>{exhibitor.get('companyName')}</strong> at
      <strong>{EVENT['eventName']}</strong> has been <strong>reviewed and confirmed</strong> by our team.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:180px;">Registration ID</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get('registrationCode')}</td></tr>
      {stall_row}
      <tr><td style="padding:6px 0;color:#666;">Event Dates</td><td style="padding:6px 0;">{EVENT['eventDatesLabel']}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Venue</td><td style="padding:6px 0;">{EVENT['venueName']}</td></tr>
    </table>

    <p>See the move-in schedule and exhibitor guidelines in your earlier registration email. We look
      forward to seeing you at the expo!</p>

    {_payment_section(exhibitor)}

    <p style="margin-bottom:0;">Team ROAR Expo</p>
  """
    return _wrap(inner)


def exhibitor_payment_reminder_email_html(exhibitor: dict) -> str:
    stall_row = (
        f'<tr><td style="padding:6px 0;color:#666;">Stall Number</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get("stallNumber")}</td></tr>'
        if exhibitor.get("stallNumber")
        else ""
    )
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">Payment reminder for your stall</h2>
    <p>Dear {exhibitor.get('contactPerson')},</p>
    <p>This is a friendly reminder to complete the payment for your stall booking with
      <strong>{exhibitor.get('companyName')}</strong> at <strong>{EVENT['eventName']}</strong>.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:180px;">Registration ID</td><td style="padding:6px 0;font-weight:bold;">{exhibitor.get('registrationCode')}</td></tr>
      {stall_row}
      <tr><td style="padding:6px 0;color:#666;">Event Dates</td><td style="padding:6px 0;">{EVENT['eventDatesLabel']}</td></tr>
    </table>

    {_payment_section(exhibitor, reminder=True)}

    <p style="margin-bottom:0;">Thank you,<br/>Team ROAR Expo</p>
  """
    return _wrap(inner)


def visitor_email_html(visitor: dict, *, has_id_card_image: bool = False) -> str:
    id_card_image = (
        """
    <div style="text-align:center;margin:18px 0;">
      <img src="cid:idcard" alt="Your ROAR Expo ID card with QR code" style="width:100%;max-width:560px;border-radius:8px;" />
    </div>
    """
        if has_id_card_image
        else ""
    )

    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">You're invited! Your registration is confirmed.</h2>
    <p>Dear {visitor.get('fullName')},</p>
    <p>Thank you for registering for <strong>{EVENT['eventName']}</strong>. Your ID card is below and
      attached to this email (also as a printable PDF) &mdash; it carries a QR code, so just show it
      on your phone (or print it) at the entrance for a quick, scan-and-go check-in.</p>
    {id_card_image}

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:180px;">Registration ID</td><td style="padding:6px 0;font-weight:bold;">{visitor.get('registrationCode')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Event Dates</td><td style="padding:6px 0;">{EVENT['eventDatesLabel']}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Timing</td><td style="padding:6px 0;">{EVENT['exhibitorInstructions']['dailyShowTiming']}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Venue</td><td style="padding:6px 0;">{EVENT['venueName']}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Guests</td><td style="padding:6px 0;">{visitor.get('numberOfGuests')}</td></tr>
    </table>

    <p>Explore <strong>{EVENT['totalStalls']} stalls</strong> across {len(EVENT['categories'])}+
      categories &mdash; from industrial machinery and robotics to jewellery, food &amp; beverage,
      healthcare, and more.</p>

    <p><a href="{EVENT['venueMapUrl']}" style="color:#0c1a33;">Get directions to the venue &rarr;</a></p>

    <p>See you at the expo!<br/>Team ROAR Expo</p>
  """

    return _wrap(inner)


def _esc(s) -> str:
    return (
        str(s if s is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def enquiry_notification_html(enquiry: dict) -> str:
    """Internal notification sent to the organizing team when someone submits
    the public Enquiry form. The visitor's own text is escaped since it's
    untrusted."""
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">New enquiry from the website</h2>
    <p>Someone has sent an enquiry through the {EVENT['eventName']} website. Reply directly to
      <a href="mailto:{_esc(enquiry.get('email'))}" style="color:#0c1a33;">{_esc(enquiry.get('email'))}</a>
      or call/WhatsApp {_esc(enquiry.get('mobile'))}.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:140px;">Name</td><td style="padding:6px 0;font-weight:bold;">{_esc(enquiry.get('name'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Email</td><td style="padding:6px 0;">{_esc(enquiry.get('email'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Mobile</td><td style="padding:6px 0;">{_esc(enquiry.get('mobile'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;vertical-align:top;">Enquiry</td><td style="padding:6px 0;white-space:pre-wrap;">{_esc(enquiry.get('details'))}</td></tr>
    </table>

    <p style="margin-bottom:0;color:#666;font-size:12px;">This enquiry is also listed in the admin dashboard's
      <strong>Enquiries</strong> tab, where it can be marked as handled.</p>
  """
    return _wrap(inner)


def enquiry_acknowledgement_html(enquiry: dict) -> str:
    """Auto-reply to the person who sent an enquiry: a branded 'we got it'
    with their own message quoted back, so they know what they asked and
    whom to expect a reply from."""
    first_name = (str(enquiry.get("name") or "").strip().split(" ") or [""])[0]
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">Thanks — we've received your enquiry</h2>
    <p>Dear {_esc(first_name or enquiry.get('name'))},</p>
    <p>Thank you for getting in touch with <strong>{EVENT['eventName']}</strong>. Your message has reached the
      organizing team and one of us will reply to you shortly &mdash; usually within one working day.</p>

    <div style="margin:18px 0;padding:14px 18px;background:#f8f6f1;border-left:3px solid #f2a93b;">
      <div style="font-size:12px;color:#666;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Your enquiry</div>
      <div style="white-space:pre-wrap;">{_esc(enquiry.get('details'))}</div>
    </div>

    <table style="width:100%;border-collapse:collapse;margin:0 0 18px;">
      <tr><td style="padding:4px 0;color:#666;width:140px;">We'll reply to</td><td style="padding:4px 0;">{_esc(enquiry.get('email'))}</td></tr>
      <tr><td style="padding:4px 0;color:#666;">Or call / WhatsApp</td><td style="padding:4px 0;">{_esc(enquiry.get('mobile'))}</td></tr>
    </table>

    <p>Meanwhile, you're welcome to explore the stall categories and venue layout on our website, or
      WhatsApp us at <strong>{EVENT['contact']['whatsapp']}</strong> (message only &mdash; no calls) if it's urgent.</p>

    <p style="margin-bottom:0;">Warm regards,<br/>Team ROAR Expo<br/>
      <span style="color:#666;font-size:12px;">{EVENT['organizers'][0]['name'] if EVENT.get('organizers') else ''}</span></p>
  """
    return _wrap(inner)


def exhibitor_alert_html(exhibitor: dict) -> str:
    """Instant heads-up to the organizing team: a new exhibitor registration
    is waiting for approval."""
    pkg = find_stall_package(exhibitor.get("stallPackage"))
    stall_rate = exhibitor.get("stallRate")
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">New exhibitor registration</h2>
    <p><strong>{_esc(exhibitor.get('companyName'))}</strong> has just registered for a stall at {EVENT['eventName']}
      and is <strong>waiting for approval</strong> in the admin dashboard.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:160px;">Registration ID</td><td style="padding:6px 0;font-weight:bold;">{_esc(exhibitor.get('registrationCode'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Company</td><td style="padding:6px 0;">{_esc(exhibitor.get('companyName'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Contact person</td><td style="padding:6px 0;">{_esc(exhibitor.get('contactPerson'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Email</td><td style="padding:6px 0;"><a href="mailto:{_esc(exhibitor.get('email'))}" style="color:#0c1a33;">{_esc(exhibitor.get('email'))}</a></td></tr>
      <tr><td style="padding:6px 0;color:#666;">Mobile</td><td style="padding:6px 0;">{_esc(exhibitor.get('phone'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Category</td><td style="padding:6px 0;">{_esc(exhibitor.get('category'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Stall package</td><td style="padding:6px 0;">{_esc(pkg['label'] if pkg else exhibitor.get('stallPackage'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Stall number</td><td style="padding:6px 0;">{_esc(exhibitor.get('stallNumber') or 'To be assigned')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Stall rate</td><td style="padding:6px 0;">{f"₹{stall_rate}" if stall_rate is not None else "To be confirmed"}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Number of stalls</td><td style="padding:6px 0;">{_esc(exhibitor.get('numberOfStalls'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;vertical-align:top;">Products / services</td><td style="padding:6px 0;white-space:pre-wrap;">{_esc(exhibitor.get('productsServices') or '—')}</td></tr>
    </table>

    <p style="margin-bottom:0;color:#666;font-size:12px;">Open the admin dashboard &rarr; <strong>Exhibitors</strong> to view the full
      registration, edit it, and approve or reject it.</p>
  """
    return _wrap(inner)


def visitor_alert_html(visitor: dict) -> str:
    """Instant heads-up to the organizing team: a new visitor registered."""
    interests = ", ".join(visitor.get("interests") or []) or "—"
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">New visitor registration</h2>
    <p><strong>{_esc(visitor.get('fullName'))}</strong> has just registered to visit {EVENT['eventName']}.</p>

    <table style="width:100%;border-collapse:collapse;margin:18px 0;">
      <tr><td style="padding:6px 0;color:#666;width:160px;">Registration code</td><td style="padding:6px 0;font-weight:bold;">{_esc(visitor.get('registrationCode'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Name</td><td style="padding:6px 0;">{_esc(visitor.get('fullName'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Email</td><td style="padding:6px 0;"><a href="mailto:{_esc(visitor.get('email'))}" style="color:#0c1a33;">{_esc(visitor.get('email'))}</a></td></tr>
      <tr><td style="padding:6px 0;color:#666;">Phone</td><td style="padding:6px 0;">{_esc(visitor.get('phone'))}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">City</td><td style="padding:6px 0;">{_esc(visitor.get('city') or '—')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Organization</td><td style="padding:6px 0;">{_esc(visitor.get('organization') or '—')}{(' · ' + _esc(visitor.get('designation'))) if visitor.get('designation') else ''}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Guests</td><td style="padding:6px 0;">{_esc(visitor.get('numberOfGuests') or 1)}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Interests</td><td style="padding:6px 0;">{_esc(interests)}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Heard about us via</td><td style="padding:6px 0;">{_esc(visitor.get('howDidYouHear') or '—')}</td></tr>
      <tr><td style="padding:6px 0;color:#666;">Source</td><td style="padding:6px 0;">{_esc(visitor.get('source') or 'online')}</td></tr>
    </table>

    <p style="margin-bottom:0;color:#666;font-size:12px;">The full list is in the admin dashboard &rarr; <strong>Visitors</strong>.</p>
  """
    return _wrap(inner)


def _site_url(path: str = "") -> str:
    import os
    base = (os.environ.get("PUBLIC_SITE_URL") or "").rstrip("/")
    return f"{base}{path}" if base else path


def exhibitor_rejected_email_html(exhibitor: dict) -> str:
    """Sent when the organizing team rejects a registration: the stall (if any)
    has been released and the exhibitor is invited to register again."""
    stall = exhibitor.get("stallNumber")
    stall_line = (
        f"<p>Stall <strong>{_esc(stall)}</strong> that you had picked has been released and is open to other exhibitors.</p>"
        if stall else ""
    )
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">About your stall registration</h2>
    <p>Dear {_esc(exhibitor.get('contactPerson'))},</p>
    <p>Thank you for your interest in <strong>{EVENT['eventName']}</strong>. We're sorry — the organizing team was
      not able to confirm the registration <strong>{_esc(exhibitor.get('registrationCode'))}</strong> for
      <strong>{_esc(exhibitor.get('companyName'))}</strong> at this time.</p>
    {stall_line}
    <p>If you would like to take part, you're welcome to register again (you can pick any stall that is still
      available on the live map) or reply to this email and our team will help you.</p>
    <p style="margin:22px 0;"><a href="{_esc(_site_url('/register/exhibitor'))}" style="background:#f2a93b;color:#0c1a33;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:999px;display:inline-block;">Register again</a></p>
    <p style="margin-bottom:0;">Team ROAR Expo</p>
  """
    return _wrap(inner)


def exhibitor_reopened_email_html(exhibitor: dict, *, stall_kept: bool) -> str:
    """Sent when an admin reopens a rejected registration: it is pending again
    and the exhibitor is asked to review / complete their details."""
    stall = exhibitor.get("stallNumber")
    if stall and stall_kept:
        stall_line = f"<p>Stall <strong>{_esc(stall)}</strong> is reserved for you again, pending confirmation.</p>"
    else:
        stall_line = ("<p>The stall you had originally picked is no longer available. Please reply with the stall you'd like "
                      "from the live map, or register again to choose one.</p>")
    inner = f"""
    <h2 style="margin-top:0;color:#0c1a33;">Your registration has been reopened</h2>
    <p>Dear {_esc(exhibitor.get('contactPerson'))},</p>
    <p>Good news — the organizing team has reopened registration <strong>{_esc(exhibitor.get('registrationCode'))}</strong>
      for <strong>{_esc(exhibitor.get('companyName'))}</strong> at <strong>{EVENT['eventName']}</strong>. It is now
      <strong>pending approval</strong> again.</p>
    {stall_line}
    <p>Please check that your details are complete and up to date. If anything has changed, fill in the registration
      form again with the correct details, or simply reply to this email with the corrections.</p>
    <p style="margin:22px 0;"><a href="{_esc(_site_url('/register/exhibitor'))}" style="background:#f2a93b;color:#0c1a33;text-decoration:none;font-weight:bold;padding:12px 22px;border-radius:999px;display:inline-block;">Open the registration form</a></p>
    <p style="margin-bottom:0;">Team ROAR Expo</p>
  """
    return _wrap(inner)
