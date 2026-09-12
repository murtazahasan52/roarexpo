"""
Short-lived stall holds while an exhibitor fills in the registration form.

Clicking a stall on the map reserves it for HOLD_MINUTES (status "held",
`tempHoldToken` + `tempHoldExpiresAt` on the stall, no exhibitor attached).
The form submits the token and claims the stall; if the exhibitor walks away
the hold simply expires and the stall is available again. Expiry is lazy —
`release_expired_holds()` runs before every stall listing / hold / claim, so
no background job is needed.

Only holds with a token expire this way; a stall held by a submitted
registration (`heldBy` set, no token) waits for the admin's decision.
"""
import os
import secrets
from datetime import timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase

from models.common import utcnow

HOLD_MINUTES = int(os.environ.get("STALL_HOLD_MINUTES") or 15)


async def release_expired_holds(db: AsyncIOMotorDatabase) -> int:
    res = await db.stalls.update_many(
        {"status": "held", "heldBy": None, "tempHoldExpiresAt": {"$lt": utcnow()}},
        {"$set": {"status": "available", "tempHoldToken": None, "tempHoldExpiresAt": None, "updatedAt": utcnow()}},
    )
    return res.modified_count


async def hold_stall(db: AsyncIOMotorDatabase, stall_number: str, previous_token: str | None = None):
    """Hold `stall_number` for the form-filling window. Returns
    (stall_doc, token, expires_at) or (None, None, None) when it is not
    available. Passing the exhibitor's previous token releases their earlier
    pick first, so switching stalls never leaves two held."""
    await release_expired_holds(db)
    if previous_token:
        await release_hold(db, previous_token)
    token = secrets.token_urlsafe(24)
    expires = utcnow() + timedelta(minutes=HOLD_MINUTES)
    stall = await db.stalls.find_one_and_update(
        {"stallNumber": stall_number, "status": "available"},
        {"$set": {"status": "held", "heldBy": None, "tempHoldToken": token, "tempHoldExpiresAt": expires, "updatedAt": utcnow()}},
        return_document=True,
    )
    if not stall:
        return None, None, None
    return stall, token, expires


async def release_hold(db: AsyncIOMotorDatabase, token: str) -> bool:
    res = await db.stalls.update_one(
        {"tempHoldToken": token, "status": "held", "heldBy": None},
        {"$set": {"status": "available", "tempHoldToken": None, "tempHoldExpiresAt": None, "updatedAt": utcnow()}},
    )
    return res.modified_count > 0


async def claim_query(db: AsyncIOMotorDatabase, stall_id, token: str | None) -> dict:
    """The filter that lets a registration take the stall: it must be
    available, or held by this very exhibitor's unexpired token."""
    await release_expired_holds(db)
    if token:
        return {"_id": stall_id, "$or": [{"status": "available"}, {"status": "held", "heldBy": None, "tempHoldToken": token}]}
    return {"_id": stall_id, "status": "available"}
