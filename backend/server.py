"""
Port of server.js — FastAPI application entrypoint. Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload   (dev)
    uvicorn server:app --host 0.0.0.0 --port 8000             (prod, behind a process manager)

Emergent (emergent.sh) and most FastAPI-on-MongoDB hosts expect this exact
file/variable name (`server.py` exposing `app`), which is why the whole
backend was restructured around it — see README.md for the full story on
why this backend exists alongside the original Node one.
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from config.db import connect_db, close_db  # noqa: E402
from routers import admin, enquiries, exhibitors, public, visitors  # noqa: E402
from seed.final_layout import ensure_final_layout  # noqa: E402
from seed.admin_seed import ensure_owner_admin  # noqa: E402
from utils.storage import init_storage, get_object  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await connect_db()
    try:
        init_storage()
        print("[storage] Object storage initialized")
    except Exception as e:  # noqa: BLE001
        print("[storage] init failed (uploads will error until resolved):", e)
    # The final venue layout ships with the app: publish it (map + all 141
    # stalls with positions) the first time this version starts, so a fresh
    # deployment comes up with the real venue and no admin step is needed.
    try:
        await ensure_final_layout(db)
    except Exception as err:  # noqa: BLE001 — never block start-up on this
        print("[layout] could not auto-publish the bundled layout:", err)
    # A fresh database gets its owner admin from ADMIN_EMAIL / ADMIN_PASSWORD.
    try:
        await ensure_owner_admin(db)
    except Exception as err:  # noqa: BLE001
        print("[seed] could not create the owner admin:", err)
    yield
    await close_db()


app = FastAPI(title="ROAR Expo API", lifespan=lifespan)

allowed_origins = [o.strip() for o in (os.environ.get("CLIENT_ORIGIN") or "").split(",") if o.strip()]

# Mirrors the old `cors({ origin: allowedOrigins.length ? allowedOrigins : true, credentials: true })`:
# a configured allow-list when CLIENT_ORIGIN is set, otherwise reflect any
# origin (allow_origin_regex=".*") while still allowing credentials.
if allowed_origins:
    app.add_middleware(
        CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware, allow_origin_regex=".*", allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )


@app.middleware("http")
async def add_uploads_cors_header(request: Request, call_next):
    """Uploaded stall-map images and exhibitor logos are fetched by the
    frontend from a different origin (e.g. Vercel) — this needs an explicit
    cross-origin resource policy, same as helmet's crossOriginResourcePolicy
    override in the old server.js."""
    response = await call_next(request)
    if request.url.path.startswith(("/uploads", "/api/uploads")):
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response


@app.get("/api/health")
async def health():
    from datetime import datetime, timezone
    return {"success": True, "message": "ROAR Expo API is running", "time": datetime.now(timezone.utc).isoformat()}


# Uploaded files (the venue map, logos, product images, ID cards) live in
# Emergent object storage and are served back here at BOTH /api/uploads and
# /uploads. Hosts route only /api/* to the backend, so the frontend always
# builds file links through the API base (see api.fileUrl) — /api/uploads/...
# works everywhere; /uploads/... is kept for older links in emails.
async def _serve_upload(path: str):
    import asyncio
    try:
        data, content_type = await asyncio.to_thread(get_object, f"roar-expo/{path}")
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/uploads/{path:path}")
async def serve_api_upload(path: str):
    return await _serve_upload(path)


@app.get("/uploads/{path:path}")
async def serve_upload(path: str):
    return await _serve_upload(path)

app.include_router(public.router)
app.include_router(exhibitors.router)
app.include_router(visitors.router)
app.include_router(admin.router)
app.include_router(enquiries.router)


# ---------- Error handling ----------
# Mirrors the old backend's JSON error shape everywhere: { success: false, message }
# so the frontend's api.js (which reads `data.message`) needs no changes at all.

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Mirrors express-validator's `{ success: false, message: "Validation
    # failed", errors: [...] }` shape from the old routes. The frontend only
    # ever reads `.message` (see StallRegistration.jsx / VisitorRegistration.jsx),
    # so the exact shape of `errors` is for parity/debugging only.
    errors = [{"msg": e.get("msg"), "loc": e.get("loc")} for e in exc.errors()]
    return JSONResponse(status_code=400, content={"success": False, "message": "Validation failed", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print("[server] Unhandled error:", repr(exc))
    return JSONResponse(status_code=500, content={"success": False, "message": f"Internal server error: {type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
