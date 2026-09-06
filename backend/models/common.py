"""
Shared helpers for turning raw Motor/PyMongo documents (plain dicts with a
`bson.ObjectId` `_id`) into JSON-safe dicts for FastAPI responses — and back.

The old Mongoose-based backend serialized documents with `_id` (as a string)
kept as `_id` (Mongoose's default `toJSON()` does NOT rename `_id` to `id`
unless you opt in with `{ toJSON: { virtuals: true } }`, which this project
never did) and `createdAt`/`updatedAt` as ISO date strings. The React
frontend reads `_id` directly everywhere (see e.g. AdminDashboard.jsx,
StallsPanel.jsx) — so this port keeps `_id` as the id field, unchanged, for
zero-diff frontend compatibility.
"""
from __future__ import annotations
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId


def is_valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


def to_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return serialize_doc(value)
    return value


def serialize_doc(doc: dict | None) -> dict | None:
    """Recursively converts ObjectId/datetime values to JSON-safe strings.
    Leaves `_id` as the key (converted to a string), matching the old
    Mongoose `toJSON()` output the frontend already expects."""
    if doc is None:
        return None
    return {k: _json_safe(v) for k, v in doc.items()}


def serialize_list(docs: list[dict]) -> list[dict]:
    return [serialize_doc(d) for d in docs]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
