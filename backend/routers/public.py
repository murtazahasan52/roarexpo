"""Port of routes/public.js + the public-facing half of controllers/
stallController.js (listStallsForPackage, getStallMap)."""
from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from config.db import get_db
from config.event_config import EVENT
from models.common import serialize_list
from models.stall_map import map_payload

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
# Without ?packageCode= it returns every stall — the registration page uses
# that to draw the full venue map (all categories) while only letting the
# exhibitor pick from the category they chose.
@router.get("/stalls")
async def list_stalls_for_package(packageCode: str | None = None, db: AsyncIOMotorDatabase = Depends(get_db)):
    projection = {"stallNumber": 1, "packageCode": 1, "size": 1, "rate": 1, "status": 1, "mapX": 1, "mapY": 1}
    query = {"packageCode": packageCode} if packageCode else {}
    cursor = db.stalls.find(query, projection).sort("stallNumber", 1)
    stalls = await cursor.to_list(length=None)
    return {"success": True, "data": serialize_list(stalls)}


@router.get("/stall-map")
async def get_stall_map(db: AsyncIOMotorDatabase = Depends(get_db)):
    stall_map = await db.stall_maps.find_one(sort=[("createdAt", -1)])
    return {"success": True, "data": map_payload(stall_map)}


# Public "Stalls" page: every stall that has a spot on the map, with the
# booking owner's name and firm for stalls that are confirmed (booked).
# Held (pending) stalls show as reserved without any exhibitor details.
@router.get("/stall-directory")
async def stall_directory(db: AsyncIOMotorDatabase = Depends(get_db)):
    stalls = await db.stalls.find({"mapX": {"$ne": None}, "mapY": {"$ne": None}}).sort("stallNumber", 1).to_list(length=None)
    booked_ids = [s["bookedBy"] for s in stalls if s.get("status") == "booked" and s.get("bookedBy")]
    owners = {}
    if booked_ids:
        for e in await db.exhibitors.find({"_id": {"$in": booked_ids}}, {"companyName": 1, "contactPerson": 1}).to_list(length=None):
            owners[e["_id"]] = {"companyName": e.get("companyName", ""), "contactPerson": e.get("contactPerson", "")}
    data = []
    for s in stalls:
        owner = owners.get(s.get("bookedBy")) if s.get("status") == "booked" else None
        data.append({
            "_id": str(s["_id"]), "stallNumber": s["stallNumber"], "packageCode": s["packageCode"],
            "status": s["status"], "mapX": s["mapX"], "mapY": s["mapY"], "owner": owner,
        })
    return {"success": True, "data": data}
