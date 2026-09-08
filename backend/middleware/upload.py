"""
Image/PDF upload validation + storage. Files arrive as FastAPI `UploadFile`
params on each router endpoint. Bytes are persisted to Emergent object storage
(see utils/storage.py) and the public URL ("/api/files/...") that the frontend
and emails embed is returned. `read_upload` returns raw bytes for callers that
need to transform them first (e.g. rendering a PDF layout to PNG).
"""
import asyncio
import pathlib

from fastapi import HTTPException, UploadFile

from utils.storage import upload_image_bytes

UPLOAD_ROOT = pathlib.Path(__file__).resolve().parent.parent / "uploads"

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
}


async def save_upload(file: UploadFile, subfolder: str, max_bytes: int) -> str:
    """Validates an uploaded image and stores it in object storage, returning
    its public URL ("/api/files/{path}") — callers store this URL directly."""
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large — max {max_bytes // (1024 * 1024)}MB")

    return await asyncio.to_thread(upload_image_bytes, contents, file.content_type, subfolder)


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
    """Uploads already-read/transformed bytes to object storage and returns the
    public URL ("/api/files/{path}")."""
    ext = (force_ext or pathlib.Path(original_name or "").suffix or ".png").lower()
    content_type = _EXT_CONTENT_TYPE.get(ext, "image/png")
    return upload_image_bytes(contents, content_type, subfolder)
