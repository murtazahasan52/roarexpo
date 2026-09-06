"""
Image upload validation + storage. Files arrive as FastAPI `UploadFile`
params on each router endpoint; `save_upload()` validates the type/size and
persists the bytes to Emergent object storage (see utils/storage.py),
returning the public URL ("/api/files/...") the frontend and emails embed.
"""
import asyncio
import pathlib

from fastapi import HTTPException, UploadFile

from utils.storage import upload_image_bytes

UPLOAD_ROOT = pathlib.Path(__file__).resolve().parent.parent / "uploads"

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

STALL_MAP_MAX_BYTES = 8 * 1024 * 1024  # 8MB
LOGO_MAX_BYTES = 5 * 1024 * 1024  # 5MB
EXHIBITOR_FILE_MAX_BYTES = 8 * 1024 * 1024  # 8MB per file


async def save_upload(file: UploadFile, subfolder: str, max_bytes: int) -> str:
    """Validates an uploaded image and stores it in object storage, returning
    its public URL ("/api/files/{path}") — callers store this URL directly."""
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large — max {max_bytes // (1024 * 1024)}MB",
        )

    return await asyncio.to_thread(upload_image_bytes, contents, file.content_type, subfolder)
