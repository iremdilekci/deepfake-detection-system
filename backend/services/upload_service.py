from __future__ import annotations

from fastapi import UploadFile

from models.video import Video
from repositories.video_repository import VideoRepository
from schemas.api_models import JobStatus, SourceType
from services.analysis_service import AnalysisService
from services.file_storage_service import FileStorageService
from services.upload_validation_service import UploadValidationService


class UploadService:
    def __init__(
        self,
        video_repository: VideoRepository,
        validator: UploadValidationService,
        file_storage: FileStorageService,
        analysis_service: AnalysisService,
    ) -> None:
        self.video_repository = video_repository
        self.validator = validator
        self.file_storage = file_storage
        self.analysis_service = analysis_service

    async def upload_file(self, file: UploadFile) -> Video:
        self.validator.validate_upload_file(file)

        video = await self.video_repository.add(
            Video(
                owner_id=None,
                original_filename=file.filename,
                stored_filename="pending",
                mime_type=file.content_type,
                status=JobStatus.uploaded.value,
            )
        )

        stored_file = await self.file_storage.save_upload(file, str(video.id))
        video.original_filename = stored_file.original_filename
        video.stored_filename = stored_file.stored_filename
        video.mime_type = stored_file.mime_type
        video.file_size_bytes = stored_file.file_size_bytes
        await self.video_repository.session.flush()

        await self.analysis_service.start_analysis(str(video.id))
        return video

    async def upload_url(self, url: str) -> Video:
        normalized_url = self.validator.validate_source_url(url)

        # Duplicate (aynı URL) kaydı kontrolü
        existing_video = await self.video_repository.get_by_source_url(normalized_url)
        if existing_video:
            # Eğer halihazırda varsa, mevcut analizi/videoyu döndür.
            # Yeniden analiz kuyruğuna sokmak yerine mevcut durumu sunarız.
            return existing_video

        video = await self.video_repository.add(
            Video(
                owner_id=None,
                source_url=normalized_url,
                stored_filename=f"{SourceType.url.value}-pending",
                status=JobStatus.uploaded.value,
            )
        )

        await self.analysis_service.start_analysis(str(video.id))
        return video
