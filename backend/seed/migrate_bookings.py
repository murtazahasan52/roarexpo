"""
Stage 3 — one-time booking migration to the 2027 floor plan.

The 2027 layout (seed/final_layout.json) renumbers most stalls. Existing
real bookings sit on the OLD stall numbers (Y* regular, L* ruby, X*/XY*
premium, plus any T/D/G/S/B beyond the new counts). `apply_final_layout`
keeps those old booked stalls around as orphans (it only deletes AVAILABLE
off-map stalls). This migration moves each orphan booking onto an equivalent
NEW stall, by category, in numeric order:

    old Regular (Y)  -> new Regular (R)
    old Ruby    (L)  -> new Ruby    (RU)
    old Premium (X)  -> new Premium (P)
    Title / Diamond / Gold / Silver / Bronze keep their number where it still
    exists; otherwise they are remapped within their own category.

Any booked stall with no free 1:1 slot in its new category is left untouched
and reported in the migration record (and the logs) for manual reassignment.

Runs once per database (guarded by a marker in the `migrations` collection),
so it also self-applies on the next production deploy — like the WhatsApp
template body migration. Must run AFTER apply_final_layout so the new stalls
already exist.
"""
import re
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.common import utcnow
from seed.final_layout import load_layout

MIGRATION_ID = "bookings-2027-01-newpdf-v1"

# old packageCode -> new packageCode
CATEGORY_MAP = {
    "regular": "regular",
    "ruby": "ruby",
    "premium": "premium",
    "title": "title",
    "diamond": "diamond",
    "gold": "gold",
    "silver": "silver",
    "bronze": "bronze",
}


def _num_key(stall_number: str):
    """Natural sort key: 'L15A' -> (15, 'A'), 'R2' -> (2, '')."""
    m = re.match(r"^[A-Z]+(\d+)([A-Z]*)$", stall_number.strip().upper())
    if not m:
        return (10**9, stall_number)
    return (int(m.group(1)), m.group(2))


async def migrate_bookings(db: AsyncIOMotorDatabase) -> dict | None:
    """Idempotent. Returns a summary dict the first time it runs, else None."""
    already = await db.migrations.find_one({"_id": MIGRATION_ID})
    if already:
        return None

    layout = load_layout()
    new_numbers = {s["stallNumber"].strip().upper() for s in layout["stalls"]}

    # Orphan bookings = booked/held stalls whose number is NOT in the new plan.
    orphans = await db.stalls.find(
        {"status": {"$in": ["booked", "held"]}, "stallNumber": {"$nin": sorted(new_numbers)}}
    ).to_list(length=None)
    orphans.sort(key=lambda s: (s.get("packageCode", ""), _num_key(s["stallNumber"])))

    moved, unmapped = [], []
    for old in orphans:
        old_num = old["stallNumber"].strip().upper()
        new_code = CATEGORY_MAP.get(old.get("packageCode", ""), old.get("packageCode", ""))
        # lowest-numbered still-available new stall in the target category
        candidates = await db.stalls.find(
            {"packageCode": new_code, "status": "available", "stallNumber": {"$in": sorted(new_numbers)}}
        ).to_list(length=None)
        candidates.sort(key=lambda s: _num_key(s["stallNumber"]))
        if not candidates:
            unmapped.append({"old": old_num, "packageCode": old.get("packageCode"),
                             "status": old.get("status"), "owner": old.get("bookedBy") or old.get("heldBy")})
            continue
        target = candidates[0]
        new_num = target["stallNumber"].strip().upper()

        # transfer the booking onto the new stall (keep new stall's own
        # rate/size/position/adminOnly — only the ownership + status move).
        await db.stalls.update_one(
            {"_id": target["_id"]},
            {"$set": {"status": old["status"], "heldBy": old.get("heldBy"),
                      "bookedBy": old.get("bookedBy"), "tempHoldToken": None,
                      "tempHoldExpiresAt": None, "updatedAt": utcnow()}},
        )
        # repoint the exhibitor(s) that referenced the old number
        owner_id = old.get("bookedBy") or old.get("heldBy")
        if owner_id:
            exs = await db.exhibitors.find({"_id": owner_id}).to_list(length=None)
            for ex in exs:
                sets = {}
                nums = ex.get("stallNumbers") or ([] if not ex.get("stallNumber") else [ex["stallNumber"]])
                nums = [new_num if (n or "").strip().upper() == old_num else n for n in nums]
                if ex.get("stallNumbers") is not None:
                    sets["stallNumbers"] = nums
                if (ex.get("stallNumber") or "").strip().upper() == old_num:
                    sets["stallNumber"] = new_num
                if ex.get("stallId") == old["_id"]:
                    sets["stallId"] = target["_id"]
                if sets:
                    sets["updatedAt"] = utcnow()
                    await db.exhibitors.update_one({"_id": ex["_id"]}, {"$set": sets})
        # drop the now-empty old stall
        await db.stalls.delete_one({"_id": old["_id"]})
        moved.append({"old": old_num, "new": new_num, "status": old["status"]})

    # Clean up any remaining OLD-layout stalls that are just available leftovers.
    removed = await db.stalls.delete_many(
        {"status": "available", "stallNumber": {"$nin": sorted(new_numbers)}}
    )

    record = {
        "_id": MIGRATION_ID,
        "appliedAt": utcnow(),
        "moved": moved,
        "unmapped": unmapped,
        "removedAvailableLeftovers": removed.deleted_count,
    }
    await db.migrations.insert_one(record)
    print(f"[migrate] Booking migration {MIGRATION_ID}: {len(moved)} bookings moved, "
          f"{len(unmapped)} unmapped (need manual reassignment), "
          f"{removed.deleted_count} old available stalls removed.")
    if unmapped:
        print("[migrate] UNMAPPED bookings (no free slot in new category — reassign manually):")
        for u in unmapped:
            print(f"    - {u['old']} ({u['packageCode']}, {u['status']})")
    return record
