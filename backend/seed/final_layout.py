"""
The FINAL venue layout, bundled with the app.

`seed/assets/final-layout.png` is the designed venue artwork (Sep 2026) and
`seed/final_layout.json` is every stall on it — number, category, printed
size and map position — produced by running the automatic detector on the
drawing and fixing the drawing's own labelling slips (see the "notes" in the
JSON). `apply_final_layout()` publishes the drawing as the current stall map
and creates/updates the stalls, so the exhibitor map and the public Stalls
page come up with the real venue from the first deploy.

Used by:
  • `python -m seed.final_layout_seed`   (command line, with .env loaded)
  • POST /api/admin/stalls/apply-bundled-layout   (admin dashboard button)

Safe to run again: stalls that already exist keep their status and booking;
only category/size/position are refreshed. Stalls NOT on this layout are
removed only when they are still `available` (a held or booked stall is never
touched) — pass replace_unplaced=False to keep them.
"""
import json
import os
import pathlib
import re

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.event_config import find_stall_package
from models.common import utcnow
from models.stall import new_stall_document
from models.stall_map import new_stall_map_document
from middleware.upload import put_object, storage_path

HERE = pathlib.Path(__file__).resolve().parent
LAYOUT_JSON = HERE / "final_layout.json"
LAYOUT_IMAGE = HERE / "assets" / "final-layout.png"
DEST_FILENAME = "final-layout.png"


def load_layout() -> dict:
    return json.loads(LAYOUT_JSON.read_text(encoding="utf-8"))


def _versioned_filename() -> str:
    """A version-specific image name so the production CDN treats each map
    update as a new resource (no stale cached artwork after a deploy)."""
    version = load_layout().get("version", "") or "v1"
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", version).strip("-") or "v1"
    return f"final-layout-{safe}.png"


def publish_image() -> tuple[str, str]:
    """Upload the bundled drawing to Emergent object storage under a
    version-specific key (cache-busting) and also under the stable key for any
    older links. Returns (filename, url). Idempotent."""
    data = LAYOUT_IMAGE.read_bytes()
    fname = _versioned_filename()
    put_object(storage_path("stall-maps", fname), data, "image/png")
    put_object(storage_path("stall-maps", DEST_FILENAME), data, "image/png")
    return fname, f"/uploads/stall-maps/{fname}"


async def ensure_final_layout(db: AsyncIOMotorDatabase) -> dict | None:
    """Start-up hook: make the bundled final layout the live map unless this
    exact version has already been published (so an admin who uploads a newer
    drawing later isn't overridden on the next restart, and bookings are
    never disturbed). Returns the apply result, or None when nothing was done.
    Switch off with AUTO_APPLY_FINAL_LAYOUT=false."""
    if (os.environ.get("AUTO_APPLY_FINAL_LAYOUT") or "true").strip().lower() in ("false", "0", "off", "no"):
        return None
    if not LAYOUT_IMAGE.exists() or not LAYOUT_JSON.exists():
        return None
    version = load_layout().get("version", "")
    already = await db.stall_maps.find_one({"detection.bundled": True, "detection.bundledVersion": version})
    if already:
        publish_image()  # keep the file in place even if uploads/ was wiped
        # A newer upload by the admin stays current; only the bundled doc is refreshed if needed.
        return None
    result = await apply_final_layout(db, replace_unplaced=False)
    print(f"[layout] Final venue layout {version} published on start-up: "
          f"{len(result['created'])} stalls created, {len(result['updated'])} refreshed, "
          f"{len(result['removed'])} sample stalls removed.")
    return result


async def apply_final_layout(db: AsyncIOMotorDatabase, *, replace_unplaced: bool = True) -> dict:
    layout = load_layout()
    if not LAYOUT_IMAGE.exists():
        raise FileNotFoundError(f"Bundled layout image missing: {LAYOUT_IMAGE}")

    # 1. Publish the drawing as the current map (a fresh copy under uploads/).
    fname, url = publish_image()
    doc = new_stall_map_document(
        fname, url, source_type="image", original_filename="final-layout.png", series=layout["series"],
    )
    doc["detection"] = {"status": "done", "applied": True, "bundled": True, "bundledVersion": layout.get("version", ""),
                        "finishedAt": utcnow(), "boxes": [], "rows": [], "prefixes": [], "ocrEngine": "bundled"}
    await db.stall_maps.insert_one(doc)

    # 2. Create or refresh every stall with its position.
    created, updated = [], []
    wanted = set()
    for s in layout["stalls"]:
        number = s["stallNumber"].strip().upper()
        wanted.add(number)
        pkg = find_stall_package(s["packageCode"]) or {}
        size = f"{pkg.get('label', s['packageCode'])} · {s['size']}" if s.get("size") else pkg.get("label", "")
        admin_only = bool(s.get("adminOnly"))
        existing = await db.stalls.find_one({"stallNumber": number})
        if existing:
            await db.stalls.update_one(
                {"_id": existing["_id"]},
                {"$set": {"packageCode": s["packageCode"], "size": size, "rate": pkg.get("rate") or 0,
                          "adminOnly": admin_only,
                          "mapX": s["mapX"], "mapY": s["mapY"],
                          "updatedAt": utcnow()}},
            )
            updated.append(number)
        else:
            stall = new_stall_document(number, s["packageCode"], pkg.get("rate") or 0, size, admin_only)
            stall["mapX"], stall["mapY"] = s["mapX"], s["mapY"]
            await db.stalls.insert_one(stall)
            created.append(number)

    # 2b. Retire stalls explicitly superseded by this layout (e.g. whole
    # L15–L27 replaced by the split L15A/L15B halves). Only remove them when
    # still available so a booked stall is never dropped from under someone.
    retired = []
    for old_number in layout.get("retiredStalls", []):
        num = str(old_number).strip().upper()
        if num in wanted:
            continue
        deleted = await db.stalls.delete_one({"stallNumber": num, "status": "available"})
        if deleted.deleted_count:
            retired.append(num)

    # 3. Retire sample stalls that are not on this drawing (only if untouched).
    removed, kept = [], []
    async for old in db.stalls.find({"stallNumber": {"$nin": sorted(wanted)}}):
        if replace_unplaced and old.get("status") == "available":
            await db.stalls.delete_one({"_id": old["_id"]})
            removed.append(old["stallNumber"])
        else:
            kept.append(old["stallNumber"])

    return {
        "mapUrl": url, "created": created, "updated": updated, "removed": removed + retired, "keptOffMap": kept,
        "notes": layout.get("notes", []), "total": len(wanted),
    }
