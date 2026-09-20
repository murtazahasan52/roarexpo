"""Port of routes/public.js + the public-facing half of controllers/
stallController.js (listStallsForPackage, getStallMap)."""
from fastapi import APIRouter, Body, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from config.db import get_db
from config.event_config import EVENT
from middleware.rate_limit import rate_limit
from models.common import serialize_doc, serialize_list
from models.stall_map import map_payload
from utils.stall_holds import HOLD_MINUTES, hold_stall, release_expired_holds, release_hold

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
    await release_expired_holds(db)
    projection = {"stallNumber": 1, "packageCode": 1, "size": 1, "rate": 1, "status": 1, "adminOnly": 1, "mapX": 1, "mapY": 1}
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
    await release_expired_holds(db)
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
            "id": str(s["_id"]), "stallNumber": s["stallNumber"], "packageCode": s["packageCode"],
            "status": s["status"], "adminOnly": bool(s.get("adminOnly")), "mapX": s["mapX"], "mapY": s["mapY"], "owner": owner,
        })
    return {"success": True, "data": data}


# ---------- Temporary hold while the registration form is being filled ----------
_hold_limiter = rate_limit("stall-hold", max_requests=60, window_seconds=15 * 60,
                           message="Too many stall selections. Please try again in a few minutes.")


@router.post("/stalls/{stall_number}/hold", dependencies=[Depends(_hold_limiter)])
async def hold_stall_for_form(stall_number: str, payload: dict | None = Body(None), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Reserve a stall for HOLD_MINUTES so nobody else can pick it while the
    exhibitor completes the form. Returns the hold token the form submits."""
    number = stall_number.strip().upper()
    stall, token, expires = await hold_stall(db, number, (payload or {}).get("previousToken"))
    if not stall:
        raise HTTPException(status_code=409, detail="That stall has just been taken by someone else. Please pick another available stall.")
    return {
        "success": True,
        "message": f"{number} is reserved for you for {HOLD_MINUTES} minutes while you complete the form.",
        "data": {"stall": serialize_doc({k: stall[k] for k in ("_id", "stallNumber", "packageCode", "rate", "status")}),
                 "holdToken": token, "expiresAt": expires.isoformat(), "holdMinutes": HOLD_MINUTES},
    }


@router.post("/stalls/release-hold")
async def release_stall_hold(payload: dict = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Give a held stall back early (the exhibitor picked another one or left)."""
    token = str((payload or {}).get("holdToken") or "")
    released = await release_hold(db, token) if token else False
    return {"success": True, "data": {"released": released}}
