import os
import uuid
import re
from pathlib import Path

import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator

from config import settings

app = FastAPI(
    title="VeraDeep API",
    description="Multimodal deepfake detection backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACCEPTED_CONTENT_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
}

ACCEPTED_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}

SUPPORTED_URL_PATTERN = re.compile(
    r"^(https?://)?(www\.)?"
    r"(youtube\.com/watch|youtu\.be/|tiktok\.com/@[\w.]+/video/"
    r"|instagram\.com/(reel|p|tv)/|twitter\.com/\w+/status/|x\.com/\w+/status/)",
    re.IGNORECASE,
)

upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)


class UploadResponse(BaseModel):
    job_id: str
    message: str
    filename: str | None = None
    source_url: str | None = None


class UrlUploadRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not SUPPORTED_URL_PATTERN.match(v.strip()):
            raise ValueError(
                "Geçerli bir YouTube, TikTok, Instagram veya Twitter/X video URL'si girin."
            )
        return v.strip()


@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "VeraDeep API"}


@app.post(
    "/upload-video",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["upload"],
    summary="Multipart video yükle",
)
async def upload_video(file: UploadFile = File(...)):
    # Content-type kontrolü
    if file.content_type not in ACCEPTED_CONTENT_TYPES:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ACCEPTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Desteklenmeyen dosya tipi: {file.content_type}. Kabul edilenler: MP4, WebM, MOV, AVI, MKV",
            )

    # Boyut kontrolü — dosyayı chunk'larla okuyarak belleği zorlamadan kontrol et
    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}{Path(file.filename or 'video').suffix.lower() or '.mp4'}"
    dest = upload_path / safe_name

    total_bytes = 0
    chunk_size = 1024 * 1024  # 1 MB

    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(chunk_size):
            total_bytes += len(chunk)
            if total_bytes > settings.max_file_size_bytes:
                await out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Dosya boyutu {settings.max_file_size_mb} MB sınırını aşıyor.",
                )
            await out.write(chunk)

    return UploadResponse(
        job_id=job_id,
        message="Video analiz kuyruğuna alındı.",
        filename=file.filename,
    )


@app.post(
    "/upload-video-url",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["upload"],
    summary="URL üzerinden video analizi",
)
async def upload_video_url(body: UrlUploadRequest):
    job_id = str(uuid.uuid4())

    return UploadResponse(
        job_id=job_id,
        message="Video linki analiz kuyruğuna alındı.",
        source_url=body.url,
    )
