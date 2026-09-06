"""
Port of seed/adminSeed.js. Run with: python -m seed.admin_seed (from the
backend_fastapi/ directory, with your .env loaded).
"""
import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from config.db import connect_db, close_db  # noqa: E402
from utils.hashing import hash_password  # noqa: E402
from models.common import utcnow  # noqa: E402


async def run():
    db = await connect_db()

    name = os.environ.get("ADMIN_NAME") or "ROAR Expo Admin"
    email = (os.environ.get("ADMIN_EMAIL") or "admin@example.com").lower().strip()
    password = os.environ.get("ADMIN_PASSWORD") or "change-me"
    # This script seeds the first/owner admin, so it always gets full access.
    # Additional, more limited admins (scanning-only, exhibitors-only, etc.)
    # should be created from the dashboard's "Admins" tab by a full-access
    # admin instead.
    permissions = ["all"]

    existing = await db.admins.find_one({"email": email})
    password_hash = hash_password(password)

    if existing:
        await db.admins.update_one(
            {"_id": existing["_id"]},
            {"$set": {"passwordHash": password_hash, "name": name, "permissions": permissions, "updatedAt": utcnow()}},
        )
        print(f"[seed] Updated existing admin: {email} (permissions: {', '.join(permissions)})")
    else:
        now = utcnow()
        await db.admins.insert_one({
            "name": name, "email": email, "passwordHash": password_hash, "permissions": permissions,
            "createdBy": None, "createdAt": now, "updatedAt": now,
        })
        print(f"[seed] Created admin: {email} (permissions: {', '.join(permissions)})")

    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
