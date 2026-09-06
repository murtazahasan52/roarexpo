"""
Emergent object storage helper. Replaces pod-local disk storage for uploaded
images (exhibitor logos, product images, admin stall-map images) and the
generated visitor ID-card PNG, so files survive redeploys and are reachable
in the deployed environment.

Files are uploaded to the platform object store and served back to clients
through this backend's own GET /api/files/{path} route (see server.py); the
stored URL for every image is therefore "/api/files/{storage_path}".
"""
import os
import uuid

import httpx

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "roar-expo"

_storage_key: str | None = None

_EXT_FROM_CT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
}


def init_storage(force: bool = False) -> str:
    """Mint (once) and cache a session-scoped storage key. force=True discards
    the cached key and mints a fresh one — the only way to recover from a key
    that went inactive mid-session."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = httpx.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    url = f"{STORAGE_URL}/objects/{path}"
    resp = httpx.put(url, headers={"X-Storage-Key": key, "Content-Type": content_type}, content=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = httpx.put(url, headers={"X-Storage-Key": key, "Content-Type": content_type}, content=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    url = f"{STORAGE_URL}/objects/{path}"
    resp = httpx.get(url, headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = httpx.get(url, headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def upload_image_bytes(data: bytes, content_type: str, subfolder: str) -> str:
    """Uploads raw image bytes to object storage under
    {app}/{subfolder}/{uuid}.{ext} and returns the public URL served by this
    backend: "/api/files/{path}"."""
    ext = _EXT_FROM_CT.get(content_type, "bin")
    path = f"{APP_NAME}/{subfolder}/{uuid.uuid4().hex}.{ext}"
    put_object(path, data, content_type)
    return f"/api/files/{path}"
