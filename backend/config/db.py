"""
MongoDB connection (Motor async driver) — Emergent-convention environment
variables: MONGO_URL (connection string, no db name in the path) + DB_NAME
(database name), instead of the single MONGODB_URI the old Express backend
used. This mirrors config/db.js's connectDB() but exposes an AsyncIOMotorDatabase
that every router/controller imports collections from.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized — call connect_db() first (on app startup).")
    return _db


async def connect_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is not None:
        return _db

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not set in the environment")
    if not db_name:
        raise RuntimeError("DB_NAME is not set in the environment")

    _client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)
    _db = _client[db_name]

    # Fail fast on a bad connection string / unreachable server, same as the
    # old backend's serverSelectionTimeoutMS behavior.
    await _client.admin.command("ping")
    print(f"[db] Connected to MongoDB: {db_name}")

    await _ensure_indexes(_db)
    return _db


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Mirrors the `unique`/`index` field options from the old Mongoose schemas."""
    await db.admins.create_index("email", unique=True)
    await db.exhibitors.create_index("registrationCode", unique=True)
    await db.exhibitors.create_index("itsNumber")
    await db.exhibitors.create_index("email")
    await db.visitors.create_index("registrationCode", unique=True)
    await db.visitors.create_index("email")
    await db.stalls.create_index("stallNumber", unique=True)
    await db.enquiries.create_index("email")
    await db.enquiries.create_index("status")


async def close_db() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None
