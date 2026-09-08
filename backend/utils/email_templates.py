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

    <p style="margin-bottom:0;">Team ROAR Expo</p>
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
      <tr><td style="padding:6px 0;color:#666;">Mobile</td><td style="padding:6px 0;">{_esc(exhibitor.get('mobile'))}</td></tr>
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
