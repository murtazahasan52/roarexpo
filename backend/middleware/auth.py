"""
Port of middleware/auth.js. JWT admin auth as FastAPI dependencies instead of
Express middleware — `Depends(require_admin)` mirrors `requireAdmin`,
`Depends(require_resource("exhibitors"))` mirrors
`requireResource("exhibitors")`, etc. All must run on a route the same way
the Express version did (after requireAdmin), which `Depends()` chaining
handles automatically since FastAPI resolves `require_admin` first.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError

from models.admin import has_permission


class AdminPayload(dict):
    """A dict subclass just so `admin.get("permissions")` reads naturally
    while still being a plain dict (matches the old `req.admin` shape:
    { id, email, name, permissions: [...] })."""


def sign_token(admin_doc: dict) -> str:
    secret = os.environ["JWT_SECRET"]
    expires_days = int(os.environ.get("JWT_EXPIRES_IN_DAYS", "365"))
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    payload = {
        "id": str(admin_doc["_id"]),
        "email": admin_doc["email"],
        "name": admin_doc["name"],
        "permissions": admin_doc.get("permissions", []),
        # JWT's "exp" claim must be a NumericDate (seconds since the Unix
        # epoch) per RFC 7519 — pass an int explicitly rather than relying
        # on a library to auto-convert a datetime, so this works the same
        # regardless of which JWT library ends up handling it.
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def require_admin(authorization: str | None = Header(default=None)) -> AdminPayload:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]

    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AdminPayload(payload)


def require_resource(resource: str):
    """Restricts a route to admins who hold "all" or the given permission."""

    async def _dep(admin: AdminPayload = Depends(require_admin)) -> AdminPayload:
        if has_permission(admin.get("permissions"), resource):
            return admin
        raise HTTPException(status_code=403, detail="You do not have access to this section")

    return _dep


def require_any_resource(resources: list[str]):
    """Restricts a route to admins who hold "all" or ANY of the given
    permissions — for routes that several different roles should reach (e.g.
    check-in, which either a "visitors" or a "scanning" admin can use)."""

    async def _dep(admin: AdminPayload = Depends(require_admin)) -> AdminPayload:
        if any(has_permission(admin.get("permissions"), r) for r in resources):
            return admin
        raise HTTPException(status_code=403, detail="You do not have access to this section")

    return _dep


async def require_full_access(admin: AdminPayload = Depends(require_admin)) -> AdminPayload:
    """Restricts a route to full-access ("all") admins only — used for
    managing other admin accounts."""
    if "all" not in (admin.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Only full-access admins can do this")
    return admin
