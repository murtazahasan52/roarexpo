"""Port of models/Stall.js."""
from pydantic import BaseModel
from models.common import utcnow

STALL_STATUS_VALUES = ["available", "held", "booked", "blocked"]


class StallCreateItem(BaseModel):
    stallNumber: str
    packageCode: str
    rate: float
    size: str | None = ""


class StallsCreateRequest(BaseModel):
    stalls: list[dict]


class StallUpdateRequest(BaseModel):
    rate: float | None = None
    packageCode: str | None = None
    size: str | None = None
    status: str | None = None
    mapX: float | None = None
    mapY: float | None = None
    # Pydantic can't tell "field omitted" from "field explicitly null" once
    # collapsed to None, but updateStall's mapX/mapY need that distinction
    # (undefined = leave alone, null = clear it). The router reads
    # `request body as raw dict` for this endpoint instead of this schema —
    # kept here for documentation/typing reference only.


def new_stall_document(stall_number: str, package_code: str, rate: float, size: str = "") -> dict:
    now = utcnow()
    return {
        "stallNumber": stall_number.strip().upper(),
        "packageCode": package_code.strip(),
        "size": size or "",
        "rate": rate,
        "status": "available",
        "heldBy": None,
        "bookedBy": None,
        "tempHoldToken": None,      # set while an exhibitor is filling the form (see utils/stall_holds.py)
        "tempHoldExpiresAt": None,
        "mapX": None,
        "mapY": None,
        "createdAt": now,
        "updatedAt": now,
    }
