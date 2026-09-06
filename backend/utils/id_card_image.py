"""
Port of utils/idCardImage.js — sharp+SVG -> Pillow. Renders a visitor's ID
card (name, registration ID, event details, and a scannable QR encoding
their registration code) as a PNG directly with Pillow draw primitives
(no SVG step needed, unlike the old Node version, since Pillow draws
raster shapes/text natively) — used both as an inline image in the
confirmation email and as the image sent over WhatsApp. Also saves it to
/uploads/id-cards so it has a public URL that WhatsApp providers (which
need a fetchable link, not raw bytes) can use.

Fonts are bundled under assets/fonts/ (DejaVu Sans) rather than relying on
system fonts being installed in whatever environment this runs in
(Emergent's container, your own server, etc.).
"""
import io
import asyncio
import pathlib
import qrcode
from PIL import Image, ImageDraw, ImageFont

from config.event_config import EVENT
from middleware.upload import UPLOAD_ROOT

CARD_W, CARD_H = 1120, 680
ID_CARDS_DIR = UPLOAD_ROOT / "id-cards"
ID_CARDS_DIR.mkdir(parents=True, exist_ok=True)

_FONTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts"
_FONT_BOLD_PATH = _FONTS_DIR / "DejaVuSans-Bold.ttf"
_FONT_REGULAR_PATH = _FONTS_DIR / "DejaVuSans.ttf"

NAVY = (12, 26, 51)
GOLD = (242, 169, 59)
WHITE = (255, 255, 255)
LIGHT_GREY = (204, 204, 204)


def _font(path: pathlib.Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


async def build_visitor_id_card_png(visitor: dict) -> dict:
    """Returns {"buffer": bytes, "filename": str, "public_url": str}. Pillow
    drawing is CPU-bound and synchronous, so it runs in a worker thread
    (`asyncio.to_thread`) rather than blocking the event loop — the old
    Node version used `sharp`, which offloads to its own native thread pool
    for the same reason."""
    return await asyncio.to_thread(_build_sync, visitor)


def _build_sync(visitor: dict) -> dict:
    qr_img = qrcode.make(visitor["registrationCode"]).resize((240, 240))

    img = Image.new("RGB", (CARD_W, CARD_H), NAVY)
    draw = ImageDraw.Draw(img)

    # Gold accent bar (left edge)
    draw.rectangle([0, 0, 24, CARD_H], fill=GOLD)

    bold_76 = _font(_FONT_BOLD_PATH, 76)
    reg_24 = _font(_FONT_REGULAR_PATH, 24)
    reg_20 = _font(_FONT_REGULAR_PATH, 20)
    bold_44 = _font(_FONT_BOLD_PATH, 44)
    reg_22 = _font(_FONT_REGULAR_PATH, 22)
    reg_18 = _font(_FONT_REGULAR_PATH, 18)
    reg_18b = _font(_FONT_BOLD_PATH, 18)
    bold_20 = _font(_FONT_BOLD_PATH, 20)

    draw.text((80, 55), "ROAR", font=bold_76, fill=GOLD)
    draw.text((80, 138), f"SAIFEE BURHANI BUSINESS EXPO — {EVENT['eventCity'].upper()}", font=reg_24, fill=WHITE)
    draw.line([(80, 200), (720, 200)], fill=GOLD, width=2)

    draw.text((80, 228), "VISITOR INVITATION", font=reg_20, fill=LIGHT_GREY)
    draw.text((80, 258), visitor.get("fullName", ""), font=bold_44, fill=WHITE)
    draw.text((80, 314), visitor.get("organization") or "", font=reg_22, fill=LIGHT_GREY)

    draw.text((80, 378), f"Registration ID:  {visitor.get('registrationCode', '')}", font=reg_22, fill=WHITE)
    draw.text((80, 414), f"Guests:  {visitor.get('numberOfGuests', 1)}", font=reg_22, fill=WHITE)

    draw.text((80, 478), EVENT["eventDatesLabel"], font=reg_22, fill=GOLD)
    draw.text((80, 514), EVENT["venueName"], font=reg_22, fill=WHITE)
    draw.text((80, 548), EVENT["exhibitorInstructions"]["dailyShowTiming"], font=reg_18, fill=LIGHT_GREY)

    # QR code panel (white background on the right)
    draw.rectangle([800, 0, CARD_W, CARD_H], fill=WHITE)
    img.paste(qr_img, (840, 180))

    scan_text = "Scan at entry"
    scan_bbox = draw.textbbox((0, 0), scan_text, font=reg_18b)
    draw.text((960 - (scan_bbox[2] - scan_bbox[0]) / 2, 424), scan_text, font=reg_18b, fill=NAVY)

    code_text = visitor.get("registrationCode", "")
    code_bbox = draw.textbbox((0, 0), code_text, font=bold_20)
    draw.text((960 - (code_bbox[2] - code_bbox[0]) / 2, 452), code_text, font=bold_20, fill=NAVY)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buffer = buf.getvalue()

    filename = f"{visitor['registrationCode']}.png"
    (ID_CARDS_DIR / filename).write_bytes(buffer)

    return {"buffer": buffer, "filename": filename, "public_url": f"/uploads/id-cards/{filename}"}
