"""
Port of utils/invitationCard.js — PDFKit -> ReportLab canvas. Builds a
printable PDF invitation card for a registered visitor (a single small
560x340pt card, not a full page), same navy/gold layout, QR panel, and
copy as the original. PDFKit positions text/shapes from the page's
top-left corner; ReportLab's canvas is bottom-left-origin, so `_top()`
below converts a "distance from the top" into the y ReportLab needs.
"""
import io
import qrcode

from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.utils import ImageReader

from config.event_config import EVENT

CARD_W, CARD_H = 560, 340
NAVY = colors.HexColor("#0c1a33")
GOLD = colors.HexColor("#f2a93b")
WHITE = colors.white
LIGHT_GREY = colors.HexColor("#cccccc")


def _top(y_from_top: float) -> float:
    """Converts a y measured down from the top of the card into the y
    ReportLab's bottom-left-origin canvas expects."""
    return CARD_H - y_from_top


def build_visitor_invitation_pdf(visitor: dict) -> bytes:
    """Returns PDF bytes (suitable for an email attachment)."""
    qr_img = qrcode.make(visitor["registrationCode"])
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    buf = io.BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=(CARD_W, CARD_H))

    # Background
    c.setFillColor(NAVY)
    c.rect(0, 0, CARD_W, CARD_H, fill=1, stroke=0)

    # Gold accent bar
    c.setFillColor(GOLD)
    c.rect(0, 0, 12, CARD_H, fill=1, stroke=0)

    # Title
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 38)
    c.drawString(40, _top(72), "R O A R")

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 12)
    c.drawString(40, _top(96), f"BUSINESS EXPO — {EVENT['eventCity'].upper()}")

    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(40, _top(106), 360, _top(106))

    c.setFillColor(LIGHT_GREY)
    c.setFont("Helvetica", 10)
    c.drawString(40, _top(122), "V I S I T O R   I N V I T A T I O N")

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, _top(146), visitor.get("fullName", ""))

    c.setFillColor(LIGHT_GREY)
    c.setFont("Helvetica", 11)
    c.drawString(40, _top(170), visitor.get("organization") or " ")

    c.setFillColor(WHITE)
    c.setFont("Helvetica", 11)
    c.drawString(40, _top(204), f"Registration ID:  {visitor.get('registrationCode', '')}")
    c.drawString(40, _top(222), f"Guests:  {visitor.get('numberOfGuests', 1)}")

    c.setFillColor(GOLD)
    c.setFont("Helvetica", 11)
    c.drawString(40, _top(254), EVENT["eventDatesLabel"])
    c.setFillColor(WHITE)
    c.drawString(40, _top(272), EVENT["venueName"])
    c.setFillColor(LIGHT_GREY)
    c.setFont("Helvetica", 9)
    c.drawString(40, _top(290), EVENT["exhibitorInstructions"]["dailyShowTiming"])

    # QR code panel
    c.setFillColor(WHITE)
    c.rect(400, 0, CARD_W - 400, CARD_H, fill=1, stroke=0)
    c.drawImage(ImageReader(qr_buf), 420, _top(210), width=120, height=120, preserveAspectRatio=True, mask="auto")
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 9)
    c.drawCentredString(480, _top(226), "Scan at entry")
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(480, _top(242), visitor.get("registrationCode", ""))

    c.showPage()
    c.save()
    return buf.getvalue()
