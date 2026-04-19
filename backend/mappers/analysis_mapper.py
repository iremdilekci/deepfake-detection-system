from __future__ import annotations

from models.analysis import AnalysisResult
from models.video import Video
from schemas.api_models import (
    JobStatus,
    JobStatusResponse,
    ModalityScore,
    ResultResponse,
    SourceType,
    UploadAcceptedResponse,
    VideoMeta,
)
from services.analysis_service import AnalysisService


def _source_type(video: Video) -> SourceType:
    return SourceType.url if video.source_url else SourceType.file


def to_upload_response(video: Video) -> UploadAcceptedResponse:
    return UploadAcceptedResponse(
        job_id=str(video.id),
        video_id=str(video.id),
        status=JobStatus(video.status),
        message="Video analiz kuyruğuna alındı.",
        source_type=_source_type(video),
        filename=video.original_filename,
        source_url=video.source_url,
    )


def to_status_response(
    video: Video,
    analysis_service: AnalysisService,
) -> JobStatusResponse:
    job_status = JobStatus(video.status)
    return JobStatusResponse(
        job_id=str(video.id),
        video_id=str(video.id),
        status=job_status,
        progress=analysis_service.calculate_progress(video),
        retryable=analysis_service.is_retryable(video),
        message=_status_message(job_status),
        source_type=_source_type(video),
        updated_at=video.updated_at,
        filename=video.original_filename,
        source_url=video.source_url,
    )


def to_result_response(video: Video, result: AnalysisResult) -> ResultResponse:
    details = result.details or {}
    modalities = [
        ModalityScore.model_validate(modality)
        for modality in details.get("modalities", [])
    ]
    errors = [result.error_message] if result.error_message else []
    final_score = result.fake_probability
    final_label = details.get("finalLabel")
    if final_label is None and result.is_fake is not None:
        final_label = "fake" if result.is_fake else "real"

    return ResultResponse(
        job_id=str(video.id),
        video_id=str(video.id),
        status=JobStatus(video.status),
        final_score=final_score,
        final_label=final_label,
        llm_explanation=details.get("llmExplanation"),
        modalities=modalities,
        video_meta=VideoMeta(
            filename=video.original_filename,
            source_type=_source_type(video),
            source_url=video.source_url,
            mime_type=video.mime_type,
            file_size_bytes=video.file_size_bytes,
            duration_seconds=video.duration_seconds,
        ),
        errors=errors,
        updated_at=video.updated_at,
    )


def _status_message(job_status: JobStatus) -> str:
    if job_status == JobStatus.queued:
        return "Analiz siraya alindi."
    if job_status == JobStatus.processing:
        return "Analiz isleniyor."
    if job_status == JobStatus.completed:
        return "Analiz tamamlandi."
    if job_status in {JobStatus.failed, JobStatus.expired}:
        return "Analiz tamamlanamadi."
    return "Icerik yuklendi."
