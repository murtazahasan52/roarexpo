"""'Ask ROAR Anything' — the website chat bot (see utils/bot_engine.py).

POST /api/bot/chat   {sessionId, message, action?}  → {success, data: {messages, quickReplies, flow, step, ai}}
GET  /api/bot/info                                   → widget bootstrap (title, whether AI answers are on)

Sessions live in the `bot_sessions` collection (TTL index, 6 hours) so the
conversation survives backend restarts and multiple workers."""
import re
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from config.bot_config import BOT, llm_settings
from config.db import get_db
from middleware.rate_limit import rate_limit
from utils.bot_engine import handle

router = APIRouter(prefix="/api/bot", tags=["bot"])

_chat_limiter = rate_limit("bot-chat", max_requests=240, window_seconds=15 * 60,
                           message="You're sending messages too quickly. Please wait a minute and try again.")

_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


async def ensure_indexes(db: AsyncIOMotorDatabase):
    try:
        await db.bot_sessions.create_index("sessionId", unique=True)
        await db.bot_sessions.create_index("expiresAt", expireAfterSeconds=0)
        # chat logs for the admin "Chats" tab — kept for 180 days
        await db.bot_logs.create_index("sessionId", unique=True)
        await db.bot_logs.create_index("updatedAt")
        await db.bot_logs.create_index("createdAt", expireAfterSeconds=180 * 24 * 3600)
        await db.bot_feedback.create_index("createdAt")
    except Exception as err:  # noqa: BLE001
        print("[bot] could not create bot_sessions indexes:", err)


@router.get("/info")
async def info():
    s = llm_settings()
    return {"success": True, "data": {
        "name": BOT["name"], "title": BOT["title"],
        "ai": bool(s["enabled"] and (s["emergent_key"] or s["openai_key"] or s["anthropic_key"])),
    }}


@router.post("/chat", dependencies=[Depends(_chat_limiter)])
async def chat(payload: dict = Body(...), db: AsyncIOMotorDatabase = Depends(get_db)):
    session_id = str((payload or {}).get("sessionId") or "")
    if not _SESSION_RE.match(session_id):
        session_id = uuid.uuid4().hex
    message = str((payload or {}).get("message") or "")
    action = (payload or {}).get("action")
    if action not in (None, "open"):
        raise HTTPException(status_code=400, detail="Unknown action")
    if not message.strip() and action != "open":
        raise HTTPException(status_code=400, detail="Type a message first")
    data = await handle(db, session_id, message, action)
    data["sessionId"] = session_id
    return {"success": True, "data": data}
