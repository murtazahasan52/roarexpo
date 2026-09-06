"""
Port of seed/stallMapSeed.js. Publishes the sample venue stall-map layout
(checked into seed/assets/sample-stall-map.jpg) as the current stall map, so
exhibitors see a reference layout on the registration page out of the box.
This is explicitly a SAMPLE — the numbering/zones in it don't need to match
the rate-card categories in config/event_config.py. Organizers can replace
it any time from the admin dashboard's "Stalls & Map" tab (Upload Map)
without touching this script again; that upload always becomes the new
"current" map, so this seed only runs its course once, the first time, when
no map has been uploaded yet.

Run with: python -m seed.stall_map_seed (from the backend_fastapi/
directory, with your .env loaded).
"""
import asyncio
import pathlib

from dotenv import load_dotenv

load_dotenv()

from config.db import connect_db, close_db  # noqa: E402
from models.stall_map import new_stall_map_document  # noqa: E402
from utils.storage import upload_image_bytes  # noqa: E402

SOURCE_ASSET = pathlib.Path(__file__).resolve().parent / "assets" / "sample-stall-map.jpg"


async def run():
    db = await connect_db()

    existing = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if existing:
        print(f"[seed] A stall map already exists ({existing['url']}) — leaving it in place. Nothing to do.")
        await close_db()
        return

    if not SOURCE_ASSET.exists():
        print(f"[seed] Sample stall map asset not found at {SOURCE_ASSET}")
        await close_db()
        return

    data = SOURCE_ASSET.read_bytes()
    url = upload_image_bytes(data, "image/jpeg", "stall-maps")
    doc = new_stall_map_document(url.rsplit("/", 1)[-1], url)
    await db.stall_maps.insert_one(doc)
    print(f"[seed] Sample stall map published: {url}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
