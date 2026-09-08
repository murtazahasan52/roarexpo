"""Renders the first page of a PDF to PNG bytes (pypdfium2 — a self-contained
wheel, no system poppler needed), so a venue layout uploaded as a PDF can be
used as the interactive stall map exactly like an image."""
import io

RENDER_SCALE = 2  # ~144 DPI — crisp enough to read stall labels on screen


def pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    try:
        import pypdfium2 as pdfium
    except ImportError as err:  # pragma: no cover
        raise RuntimeError("PDF support isn't installed on the server (pypdfium2 missing) — upload a PNG/JPG of the layout instead") from err

    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        if len(pdf) == 0:
            raise RuntimeError("The PDF has no pages")
        page = pdf[0]
        bitmap = page.render(scale=RENDER_SCALE)
        image = bitmap.to_pil().convert("RGB")
    finally:
        pdf.close()

    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
