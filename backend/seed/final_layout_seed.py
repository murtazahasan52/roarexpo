"""
Publish the bundled FINAL venue layout and its stalls (see seed/final_layout.py).

Run with: python -m seed.final_layout_seed [--keep-old]
(from the backend_fastapi/ directory, with your .env loaded).

--keep-old   don't remove sample stalls that are not on the final drawing
             (held/booked stalls are never removed either way).
"""
import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from config.db import connect_db, close_db  # noqa: E402
from seed.final_layout import apply_final_layout  # noqa: E402


async def run():
    db = await connect_db()
    result = await apply_final_layout(db, replace_unplaced="--keep-old" not in sys.argv)
    print(f"[seed] Final layout published: {result['mapUrl']}")
    print(f"[seed] Stalls: {len(result['created'])} created, {len(result['updated'])} refreshed, "
          f"{len(result['removed'])} old sample stalls removed, {len(result['keptOffMap'])} kept (booked/held or --keep-old). "
          f"{result['total']} stalls on the map.")
    for n in result["notes"]:
        print("[seed] note:", n)
    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
