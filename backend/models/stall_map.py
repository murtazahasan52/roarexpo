"""Port of models/StallMap.js. Only one stall map is ever "current" — we
simply keep every upload as a row and always read the most recently created
one (see routers/public.get_stall_map / routers/admin.upload_stall_map)."""
from models.common import utcnow


def new_stall_map_document(filename: str, url: str) -> dict:
    now = utcnow()
    return {"filename": filename, "url": url, "createdAt": now, "updatedAt": now}
