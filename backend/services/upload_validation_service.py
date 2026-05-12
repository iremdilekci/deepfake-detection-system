from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from config import settings


class UploadValidationService:
    accepted_content_types = {
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-matroska",
    }
    accepted_extensions = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
    supported_url_pattern = re.compile(
        r"^(https?://)?(www\.)?"
        r"(youtube\.com/watch|youtu\.be/|tiktok\.com/@[\w.]+/video/"
        r"|instagram\.com/(reel|p|tv)/|twitter\.com/\w+/status/|x\.com/\w+/status/)",
        re.IGNORECASE,
    )

    def validate_upload_file(self, file: UploadFile) -> None:
        if not file.filename or not file.filename.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dosya adı null veya bozuk olamaz."
            )

        extension = Path(file.filename).suffix.lower()
        if not extension:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Geçerli bir dosya uzantısı bulunamadı."
            )

        has_valid_content_type = file.content_type in self.accepted_content_types
        has_valid_extension = extension in self.accepted_extensions

        # Content type tek başına güvenli değil; uzantı kontrolü istemci/sunucu tutarlılığı sağlar.
        if not has_valid_content_type and not has_valid_extension:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Desteklenmeyen dosya tipi: {file.content_type}. "
                    "Kabul edilenler: MP4, WebM, MOV, AVI, MKV"
                ),
            )

    def validate_source_url(self, url: str) -> str:
        normalized = url.strip()
        if not self.supported_url_pattern.match(normalized):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Geçerli bir YouTube, TikTok, Instagram veya "
                    "Twitter/X video URL'si girin."
                ),
            )
        return normalized

    def ensure_size_within_limit(self, total_bytes: int) -> None:
        if total_bytes > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Dosya boyutu {settings.max_file_size_mb} MB sınırını aşıyor.",
            )
