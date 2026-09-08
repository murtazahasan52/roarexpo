"""Port of models/StallMap.js. Only one stall map is ever "current" — we
simply keep every upload as a row and always read the most recently created
one (see routers/public.get_stall_map / routers/admin.upload_stall_map).

`series` records which letter series drawn on the layout belongs to which
rate-card category (e.g. prefix "G" → gold, "R" → regular) and whether the
labels use a separator ("" → G1, "-" → G-1). It drives "generate stalls from
layout" and lets the public map group markers by category."""
import re

from config.event_config import EVENT
from models.common import utcnow

_PREFIX_RE = re.compile(r"^[A-Z]{1,4}$")


def new_stall_map_document(filename: str, url: str, *, source_type: str = "image",
                           original_filename: str = "", series: list | None = None) -> dict:
    now = utcnow()
    return {
        "filename": filename,
        "url": url,
        "sourceType": source_type,
        "originalFilename": original_filename,
        "series": series or [],
        "createdAt": now,
        "updatedAt": now,
    }


def map_payload(doc: dict | None) -> dict | None:
    if not doc:
        return None
    from models.common import serialize_doc
    return {
        "url": doc["url"],
        "uploadedAt": serialize_doc({"v": doc.get("createdAt")})["v"],
        "sourceType": doc.get("sourceType") or "image",
        "series": doc.get("series") or [],
    }


def parse_series(raw) -> tuple[list | None, str | None]:
    """Validates a series list. Returns (series, None) or (None, error).
    `raw` may be a JSON string (multipart form field) or a list."""
    import json
    if raw is None:
        return None, None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None, "series must be a JSON array"
    if not isinstance(raw, list):
        return None, "series must be an array"
    valid_codes = {p["code"] for p in EVENT["stallPackages"]}
    seen = set()
    series = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        prefix = str(s.get("prefix") or "").strip().upper()
        package_code = str(s.get("packageCode") or "").strip()
        separator = "-" if s.get("separator") == "-" else ""
        if not prefix or not package_code:
            continue
        if not _PREFIX_RE.match(prefix):
            return None, f'Series prefix "{prefix}" must be 1–4 letters (e.g. G, R, RU)'
        if package_code not in valid_codes:
            return None, f'Unknown category "{package_code}"'
        if prefix in seen:
            return None, f'Series prefix "{prefix}" is listed twice'
        seen.add(prefix)
        series.append({"prefix": prefix, "packageCode": package_code, "separator": separator})
    return series, None
