from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class JobStatus(str, Enum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    expired = "expired"


class SourceType(str, Enum):
    file = "file"
    url = "url"


class UrlUploadRequest(ApiModel):
    url: str

    @field_validator("url")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Video URL alanı boş bırakılamaz.")
        return normalized


class UploadAcceptedResponse(ApiModel):
    job_id: str
    video_id: str
    status: JobStatus
    message: str
    source_type: SourceType
    filename: str | None = None
    source_url: str | None = None


class AnalyzeRequest(ApiModel):
    retry_failed: bool = False


class JobStatusResponse(ApiModel):
    job_id: str
    video_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    retryable: bool
    message: str
    source_type: SourceType
    updated_at: datetime
    filename: str | None = None
    source_url: str | None = None


class ModalityScore(ApiModel):
    key: Literal["visual", "audio", "text"]
    label: str
    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    verdict: Literal["fake", "real", "uncertain"]


class VideoMeta(ApiModel):
    filename: str | None = None
    source_type: SourceType
    source_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None


class ChartDataset(ApiModel):
    label: str
    data: list[float]

class ChartData(ApiModel):
    labels: list[str]
    datasets: list[ChartDataset]


class ResultResponse(ApiModel):
    job_id: str
    video_id: str
    status: JobStatus
    final_score: float | None = Field(default=None, ge=0, le=1)
    final_label: Literal["fake", "real", "uncertain"] | None = None
    llm_explanation: str | None = None
    text_explanations: list[str] = Field(default_factory=list)
    modalities: list[ModalityScore] = Field(default_factory=list)
    chart_data: ChartData | None = None
    video_meta: VideoMeta
    errors: list[str] = Field(default_factory=list)
    updated_at: datetime
