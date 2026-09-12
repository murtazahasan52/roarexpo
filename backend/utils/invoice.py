"""
Port of utils/invoice.js — PDFKit -> ReportLab. Builds a simple, non-GST
stall booking-summary PDF for an exhibitor (NOT a tax invoice — payment is
handled offline by the organizing team, so this intentionally carries no
GSTIN, tax breakdown, or bank details), same content and section order as
the original, using ReportLab's Platypus flowables (Table/Paragraph) rather
than PDFKit's manual x/y positioning — much easier to keep correct as
content grows/shrinks, while keeping the same navy/gold brand palette,
header band, exhibitor details block, booking table, and footer note.
"""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import Flowable

from config.event_config import EVENT, find_stall_package

NAVY = colors.HexColor("#0c1a33")
GOLD = colors.HexColor("#f2a93b")
MUTED = colors.HexColor("#6b7385")
INK = colors.HexColor("#101c33")
LINE = colors.HexColor("#e9e4d8")
SLATE = colors.HexColor("#3c4657")

HEADER_HEIGHT = 24 * mm


def _format_amount(n) -> str:
    if n is None:
        return "To be confirmed"
    return f"Rs. {int(n):,}"


def _format_date(d) -> str:
    if d is None:
        d = datetime.now(timezone.utc)
    return d.strftime("%d %b %Y")


class _HeaderBand(Flowable):
    """Draws the navy header band with the ROAR wordmark + event name, and
    the 'STALL BOOKING SUMMARY' title on the right — matches the original
    PDFKit header block. Text is inset by the page's own left/right margins
    so it lines up with the body content below it, same as the original
    (which positioned its header text at `doc.page.margins.left`)."""

    def __init__(self, width, margin):
        super().__init__()
        self.width = width
        self.height = HEADER_HEIGHT
        self.margin = margin

    def draw(self):
        c = self.canv
        c.setFillColor(NAVY)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(self.margin, self.height - 34, "ROAR")
        c.setFillColor(colors.white)
        c.setFont("Helvetica", 9)
        c.drawString(self.margin, self.height - 50, EVENT["eventName"].upper())
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(self.width - self.margin, self.height - 34, "STALL BOOKING SUMMARY")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(colors.HexColor("#c9d1e0"))
        c.drawRightString(self.width - self.margin, self.height - 50, f"{EVENT['venueName']}  ·  {EVENT['eventDatesLabel']}")


def build_exhibitor_invoice_pdf(exhibitor: dict) -> bytes:
    """Returns PDF bytes (suitable for a direct download/inline response)."""
    stall_package_info = find_stall_package(exhibitor.get("stallPackage"))
    package_label = (stall_package_info or {}).get("label") or exhibitor.get("stallPackage") or "—"
    inclusions = (stall_package_info or {}).get("inclusions") or ""
    quantity = exhibitor.get("numberOfStalls") or 1
    # The rate captured at registration wins; a registration made without a
    # numbered stall falls back to the category's rate-card price so the
    # summary still shows an amount rather than "to be confirmed".
    rate = exhibitor.get("stallRate")
    if rate is None:
        rate = (stall_package_info or {}).get("rate")
    total = rate * quantity if rate is not None else None

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=50, rightMargin=50, topMargin=36 + HEADER_HEIGHT, bottomMargin=50,
        title=f"ROAR Expo Booking Summary {exhibitor.get('registrationCode', '')}",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=lambda c, d: _draw_header(c, d, margin=50))])

    label_style = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=10, textColor=SLATE, spaceAfter=2)
    value_style = ParagraphStyle("value", fontName="Helvetica", fontSize=11, leading=14, textColor=INK)
    section_style = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#b8740f"))
    company_style = ParagraphStyle("company", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=INK, spaceBefore=4, spaceAfter=3)
    body_style = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, textColor=SLATE, leading=14)
    footer_style = ParagraphStyle("footer", fontName="Helvetica", fontSize=9, textColor=MUTED, leading=12)
    footer_contact_style = ParagraphStyle("footer_contact", fontName="Helvetica", fontSize=9.5, textColor=SLATE, leading=13)

    story = []

    ref_table = Table(
        [
            [Paragraph("Reference No.", label_style), Paragraph("Date Issued", label_style), Paragraph("Booking Status", label_style)],
            [
                Paragraph(exhibitor.get("registrationCode", ""), value_style),
                Paragraph(_format_date(None), value_style),
                Paragraph(
                    {"approved": "Confirmed", "confirmed": "Confirmed", "rejected": "Cancelled", "cancelled": "Cancelled"}.get(
                        exhibitor.get("status"), "Pending approval"
                    ),
                    value_style,
                ),
            ],
        ],
        colWidths=[doc.width / 3] * 3,
    )
    ref_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, 0), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("LINEBELOW", (0, 1), (-1, 1), 1, LINE),
    ]))
    story.append(ref_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("EXHIBITOR", section_style))
    story.append(Paragraph(exhibitor.get("companyName", ""), company_style))

    address_lines = [exhibitor.get("contactPerson", "")]
    if exhibitor.get("businessAddress"):
        address_lines.append(exhibitor["businessAddress"])
    city_line = ", ".join(filter(None, [exhibitor.get("city"), exhibitor.get("state"), exhibitor.get("pincode")]))
    if city_line:
        address_lines.append(city_line)
    address_lines.append(f"{exhibitor.get('email', '')}  ·  {exhibitor.get('phone', '')}")
    story.append(Paragraph("<br/>".join(address_lines), body_style))
    story.append(Spacer(1, 10))

    # ---------- Booking table ----------
    header_row = [
        Paragraph("DESCRIPTION", ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white)),
        Paragraph("STALL NO.", ParagraphStyle("th2", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white)),
        Paragraph("QTY", ParagraphStyle("th3", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white)),
        Paragraph("AMOUNT", ParagraphStyle("th4", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=TA_RIGHT)),
    ]
    desc_html = f"<b>{package_label}</b>"
    if inclusions:
        desc_html += f'<br/><font size="9" color="#6b7385">{inclusions}</font>'
    row = [
        Paragraph(desc_html, ParagraphStyle("desc", fontName="Helvetica", fontSize=11, textColor=INK, leading=14)),
        Paragraph(exhibitor.get("stallNumber") or "Not yet assigned", value_style),
        Paragraph(str(quantity), value_style),
        Paragraph(
            _format_amount(rate * quantity if rate is not None else None),
            ParagraphStyle("amt", fontName="Helvetica-Bold", fontSize=10.5, textColor=INK, alignment=TA_RIGHT),
        ),
    ]
    booking_table = Table([header_row, row], colWidths=[doc.width * 0.5, doc.width * 0.22, doc.width * 0.14, doc.width * 0.14])
    booking_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, 1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, 1), 1, LINE),
    ]))
    story.append(booking_table)
    story.append(Spacer(1, 10))

    if exhibitor.get("fasciaName"):
        story.append(Paragraph(
            f"Fascia name: {exhibitor['fasciaName']}",
            ParagraphStyle("fascia", fontName="Helvetica", fontSize=9.5, textColor=MUTED),
        ))
        story.append(Spacer(1, 10))

    total_table = Table(
        [[
            "",
            Paragraph("Total", ParagraphStyle("total_label", fontName="Helvetica-Bold", fontSize=12, textColor=INK)),
            Paragraph(_format_amount(total), ParagraphStyle("total_amt", fontName="Helvetica-Bold", fontSize=12, textColor=INK, alignment=TA_RIGHT)),
        ]],
        colWidths=[doc.width * 0.5, doc.width * 0.22, doc.width * 0.28],
    )
    total_table.setStyle(TableStyle([
        ("LINEABOVE", (1, 0), (-1, 0), 1, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 26))

    story.append(Paragraph(
        "This is a simple stall-booking summary and not a GST tax invoice — no tax is charged at the time of "
        "booking. Payment terms and final settlement will be shared separately by the organizing team.",
        footer_style,
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"{EVENT['venueName']}  ·  {EVENT['eventDatesLabel']}", footer_contact_style))
    story.append(Paragraph(
        f"{EVENT['contact']['email']}  ·  {EVENT['contact']['whatsapp']} ({EVENT['contact']['whatsappNote']})",
        footer_contact_style,
    ))

    doc.build(story)
    return buf.getvalue()


def _draw_header(canvas_obj, doc, margin=50):
    canvas_obj.saveState()
    canvas_obj.translate(0, doc.pagesize[1] - HEADER_HEIGHT)
    band = _HeaderBand(doc.pagesize[0], margin)
    band.canv = canvas_obj
    band.draw()
    canvas_obj.restoreState()
