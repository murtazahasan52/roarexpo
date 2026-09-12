"""
Image/PDF upload validation + storage. Files arrive as FastAPI `UploadFile`
params on each router endpoint. Bytes are persisted to Emergent object storage
(see utils/storage.py) under `roar-expo/{subfolder}/{filename}`, and the
unique filename is returned — callers build the same `/uploads/{subfolder}/{filename}`
URL the old backend returned. Those URLs are served back (from object storage)
by the GET /api/uploads/{path} route in server.py, so nothing is written to the
pod-local disk (which is wiped on redeploy).
"""
import time
import random
import pathlib
import asyncio

from fastapi import HTTPException, UploadFile

from utils.storage import put_object, get_object  # noqa: F401 (get_object re-exported for server route)

STORAGE_APP = "roar-expo"

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

STALL_MAP_MAX_BYTES = 15 * 1024 * 1024  # 15MB — PDFs of full venue drawings can be large
MAP_TYPES = IMAGE_TYPES | {"application/pdf"}
LOGO_MAX_BYTES = 5 * 1024 * 1024  # 5MB
EXHIBITOR_FILE_MAX_BYTES = 8 * 1024 * 1024  # 8MB per file

_EXT_CONTENT_TYPE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _unique_filename(original_name: str) -> str:
    ext = pathlib.Path(original_name or "").suffix
    return f"{int(time.time() * 1000)}-{random.randint(0, 999999999)}{ext}"


def storage_path(subfolder: str, filename: str) -> str:
    return f"{STORAGE_APP}/{subfolder}/{filename}"


def _content_type_for(filename: str, fallback: str = "image/png") -> str:
    return _EXT_CONTENT_TYPE.get(pathlib.Path(filename).suffix.lower(), fallback)


async def save_upload(file: UploadFile, subfolder: str, max_bytes: int) -> str:
    """Validates an uploaded image, stores it in object storage and returns its
    unique filename (callers build the /uploads/{subfolder}/{filename} URL)."""
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large — max {max_bytes // (1024 * 1024)}MB")

    filename = _unique_filename(file.filename or "")
    await asyncio.to_thread(put_object, storage_path(subfolder, filename), contents, file.content_type)
    return filename


async def read_upload(file: UploadFile, allowed_types: set[str], max_bytes: int, type_error: str) -> bytes:
    """Validates type/size and returns the raw bytes (caller decides what to
    write) — used by the layout upload, which may need to convert a PDF."""
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=type_error)
    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large — max {max_bytes // (1024 * 1024)}MB")
    return contents


def write_upload_bytes(contents: bytes, subfolder: str, original_name: str, force_ext: str | None = None) -> str:
    """Stores already-read/transformed bytes in object storage; returns the filename."""
    filename = _unique_filename(original_name)
    if force_ext:
        filename = pathlib.Path(filename).with_suffix(force_ext).name
    put_object(storage_path(subfolder, filename), contents, _content_type_for(filename))
    return filename
