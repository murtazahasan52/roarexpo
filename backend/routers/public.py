"""Port of routes/public.js + the public-facing half of controllers/
stallController.js (listStallsForPackage, getStallMap)."""
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from config.db import get_db
from config.event_config import EVENT
from models.common import serialize_doc, serialize_list

router = APIRouter(prefix="/api/public", tags=["public"])


# Publicly safe subset of event config, consumed by the frontend so copy
# stays in sync in one place. Contact/pricing/instructions are intentionally
# included since they're shown on the public site too.
@router.get("/config")
async def get_config():
    return {"success": True, "data": EVENT}


# All stalls in a category (?packageCode=, required) — any status, so the
# exhibitor registration page can render its map-click picker (available =
# selectable, held = "pending confirmation", booked = "confirmed", blocked =
# unavailable) and disable re-selection of anything that isn't available.
# Never selects heldBy/bookedBy, so no exhibitor identity is exposed on this
# public endpoint — only the stall's own status (and its mapX/mapY marker
# position, if an admin has placed it).
@router.get("/stalls")
async def list_stalls_for_package(packageCode: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    if not packageCode:
        raise HTTPException(status_code=400, detail="packageCode is required")

    projection = {"stallNumber": 1, "packageCode": 1, "size": 1, "rate": 1, "status": 1, "mapX": 1, "mapY": 1}
    cursor = db.stalls.find({"packageCode": packageCode}, projection).sort("stallNumber", 1)
    stalls = await cursor.to_list(length=None)
    return {"success": True, "data": serialize_list(stalls)}


@router.get("/stall-map")
async def get_stall_map(db: AsyncIOMotorDatabase = Depends(get_db)):
    stall_map = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    if not stall_map:
        return {"success": True, "data": None}
    return {"success": True, "data": {"url": stall_map["url"], "uploadedAt": serialize_doc(stall_map)["createdAt"]}}
