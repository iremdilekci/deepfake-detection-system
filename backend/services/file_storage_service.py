from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from fastapi import UploadFile

from services.upload_validation_service import UploadValidationService


@dataclass(slots=True)
class StoredFile:
    stored_filename: str
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int


class FileStorageService:
    def __init__(
        self,
        upload_dir: str,
        validator: UploadValidationService,
    ) -> None:
        self.upload_path = Path(upload_dir)
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.validator = validator

    async def save_upload(self, file: UploadFile, job_id: str) -> StoredFile:
        import aiofiles

        extension = Path(file.filename or "video").suffix.lower() or ".mp4"
        safe_name = f"{job_id}{extension}"
        destination = self.upload_path / safe_name
        total_bytes = 0
        chunk_size = 1024 * 1024

        try:
            async with aiofiles.open(destination, "wb") as output_file:
                while chunk := await file.read(chunk_size):
                    total_bytes += len(chunk)
                    self.validator.ensure_size_within_limit(total_bytes)
                    await output_file.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        return StoredFile(
            stored_filename=safe_name,
            original_filename=file.filename,
            mime_type=file.content_type,
            file_size_bytes=total_bytes,
        )
