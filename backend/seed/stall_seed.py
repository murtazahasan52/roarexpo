"""
Port of seed/stallSeed.js. Generates the sample stall inventory for every
rate-card category that has an online stall-number picker (Food Court /
Play Zone are sq.ft-based and intentionally have no numbered stalls — see
config/event_config.py). Safe to run more than once: existing stall numbers
are left untouched, only missing ones are created, so this never overwrites
live booking status.

Run with: python -m seed.stall_seed (from the backend_fastapi/ directory,
with your .env loaded).
"""
import asyncio

from dotenv import load_dotenv

load_dotenv()

from config.db import connect_db, close_db  # noqa: E402
from config.event_config import numbered_packages  # noqa: E402
from models.stall import new_stall_document  # noqa: E402

# Numbering scheme (short prefix + sequence number), independent of any
# venue map image so it stays valid no matter what layout the organizers
# upload later:
PREFIXES = {
    "title": "T", "diamond": "D", "gold": "G", "silver": "S",
    "bronze": "B", "premium": "P", "regular": "R", "ruby": "RU",
}


async def run():
    db = await connect_db()

    to_create = []
    for pkg in numbered_packages():
        prefix = PREFIXES.get(pkg["code"], pkg["code"][:2].upper())
        count = pkg.get("stallCount") or 0
        for i in range(1, count + 1):
            to_create.append({
                "stallNumber": f"{prefix}-{i}", "packageCode": pkg["code"], "size": pkg["label"], "rate": pkg["rate"],
            })

    created = 0
    skipped = 0
    for s in to_create:
        existing = await db.stalls.find_one({"stallNumber": s["stallNumber"]})
        if existing:
            skipped += 1
            continue
        await db.stalls.insert_one(new_stall_document(s["stallNumber"], s["packageCode"], s["rate"], s["size"]))
        created += 1

    print(f"[seed] Stalls: {created} created, {skipped} already existed (skipped). Total defined: {len(to_create)}.")

    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
