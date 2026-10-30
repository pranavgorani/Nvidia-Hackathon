import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/pjpeg"
}

# Magic signatures
MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg"
}

class StorageService:
    def __init__(self, upload_dir: str = settings.STORAGE_PATH):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_upload(self, file: UploadFile, org_id: str) -> dict:
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File extension '{ext}' not supported. Allowed: PDF, PNG, JPG, JPEG."
            )

        # Read first 16 bytes for magic signature validation
        header = await file.read(16)
        await file.seek(0)

        is_valid_magic = False
        for magic, _ in MAGIC_SIGNATURES.items():
            if header.startswith(magic):
                is_valid_magic = True
                break

        if not is_valid_magic:
            raise HTTPException(
                status_code=400,
                detail="File signature validation failed. File content does not match allowed PDF or image types."
            )

        # Generate opaque storage name
        opaque_name = f"{org_id}_{uuid.uuid4().hex}{ext}"
        storage_path = os.path.join(self.upload_dir, opaque_name)

        total_size = 0
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        async with aiofiles.open(storage_path, "wb") as out_file:
            while chunk := await file.read(1024 * 64):
                total_size += len(chunk)
                if total_size > max_bytes:
                    os.remove(storage_path)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                await out_file.write(chunk)

        return {
            "opaque_filename": opaque_name,
            "original_name": filename,
            "mime_type": file.content_type or "application/octet-stream",
            "file_size": total_size,
            "storage_path": storage_path
        }

storage_service = StorageService()

