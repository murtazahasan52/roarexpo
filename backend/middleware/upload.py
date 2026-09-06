"""
Port of middleware/upload.js. Multer saved files to disk with a random
filename and exposed `req.file` / `req.files`; here each router endpoint
receives `UploadFile` params directly (FastAPI's own multipart handling) and
calls `save_upload()` below to write it to the matching /uploads subfolder
with an equivalent unique filename, then builds the same `/uploads/...` URL
the old backend returned.
"""
import time
import random
import pathlib

from fastapi import HTTPException, UploadFile

UPLOAD_ROOT = pathlib.Path(__file__).resolve().parent.parent / "uploads"

for sub in ("stall-maps", "logos", "product-images", "id-cards"):
    (UPLOAD_ROOT / sub).mkdir(parents=True, exist_ok=True)

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}

STALL_MAP_MAX_BYTES = 8 * 1024 * 1024  # 8MB
LOGO_MAX_BYTES = 5 * 1024 * 1024  # 5MB
EXHIBITOR_FILE_MAX_BYTES = 8 * 1024 * 1024  # 8MB per file


def _unique_filename(original_name: str) -> str:
    ext = pathlib.Path(original_name or "").suffix
    unique = f"{int(time.time() * 1000)}-{random.randint(0, 999999999)}{ext}"
    return unique


async def save_upload(file: UploadFile, subfolder: str, max_bytes: int) -> str:
    """Validates and saves an uploaded image, returning its new filename
    (not the full /uploads/... URL — callers build that, same as the old
    controllers did with `req.file.filename`)."""
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP images are allowed")

    contents = await file.read()
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large — max {max_bytes // (1024 * 1024)}MB",
        )

    filename = _unique_filename(file.filename or "")
    dest = UPLOAD_ROOT / subfolder / filename
    dest.write_bytes(contents)
    return filename
