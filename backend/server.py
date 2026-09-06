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
import pathlib
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

from config.db import connect_db, close_db  # noqa: E402
from routers import admin, exhibitors, public, visitors  # noqa: E402
from utils.storage import get_object, init_storage  # noqa: E402

UPLOAD_ROOT = pathlib.Path(__file__).resolve().parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    try:
        init_storage()
        print("[storage] Object storage initialized")
    except Exception as e:  # noqa: BLE001
        print("[storage] init failed (uploads will error until resolved):", e)
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
    if request.url.path.startswith("/uploads"):
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response


@app.get("/api/health")
async def health():
    from datetime import datetime, timezone
    return {"success": True, "message": "ROAR Expo API is running", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/files/{path:path}")
async def serve_file(path: str):
    """Serves images stored in Emergent object storage (exhibitor logos,
    product images, stall maps, visitor ID cards). Public, since these are
    shown on the registration site and in emails."""
    import asyncio
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

app.include_router(public.router)
app.include_router(exhibitors.router)
app.include_router(visitors.router)
app.include_router(admin.router)


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
    print("[server] Unhandled error:", exc)
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
