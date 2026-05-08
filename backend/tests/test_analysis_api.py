from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import settings
from main import create_app, get_analysis_service, get_upload_service
from services.upload_validation_service import UploadValidationService


@dataclass
class FakeVideo:
    id: uuid.UUID
    status: str
    original_filename: str | None = None
    stored_filename: str = "stored.mp4"
    source_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class FakeResult:
    status: str = "pending"
    details: dict | None = None
    error_message: str | None = None
    is_fake: bool | None = None
    confidence_score: float | None = None
    fake_probability: float | None = None
    real_probability: float | None = None


class InMemoryAnalysisStore:
    def __init__(self) -> None:
        self.jobs: dict[str, FakeVideo] = {}
        self.results: dict[str, FakeResult] = {}
        self.poll_count: dict[str, int] = {}

    def create_file_job(self, filename: str | None, mime_type: str | None, file_size: int) -> FakeVideo:
        video_id = uuid.uuid4()
        video = FakeVideo(
            id=video_id,
            status="queued",
            original_filename=filename,
            stored_filename=f"{video_id}.mp4",
            mime_type=mime_type,
            file_size_bytes=file_size,
            updated_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.jobs[str(video_id)] = video
        self.results[str(video_id)] = FakeResult()
        self.poll_count[str(video_id)] = 0
        return video

    def create_url_job(self, url: str) -> FakeVideo:
        video_id = uuid.uuid4()
        video = FakeVideo(
            id=video_id,
            status="queued",
            source_url=url,
            stored_filename=f"url-{video_id}",
            updated_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.jobs[str(video_id)] = video
        self.results[str(video_id)] = FakeResult()
        self.poll_count[str(video_id)] = 0
        return video

    def resolve(self, job_id: str) -> tuple[FakeVideo, FakeResult]:
        try:
            return self.jobs[job_id], self.results[job_id]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="İlgili analiz işi bulunamadı.") from exc


class FakeUploadService:
    def __init__(self, store: InMemoryAnalysisStore) -> None:
        self.store = store
        self.validator = UploadValidationService()

    async def upload_file(self, file) -> FakeVideo:
        self.validator.validate_upload_file(file)
        contents = await file.read()
        self.validator.ensure_size_within_limit(len(contents))
        await file.close()
        return self.store.create_file_job(file.filename, file.content_type, len(contents))

    async def upload_url(self, url: str) -> FakeVideo:
        normalized_url = self.validator.validate_source_url(url)
        return self.store.create_url_job(normalized_url)


class FakeAnalysisService:
    def __init__(self, store: InMemoryAnalysisStore) -> None:
        self.store = store

    async def start_analysis(self, job_id: str, retry_failed: bool = False):
        video, result = self.store.resolve(job_id)
        if video.status == "failed" and not retry_failed:
            raise HTTPException(status_code=409, detail="Retry gerekli.")

        video.status = "queued"
        result.status = "pending"
        result.error_message = None
        self.store.poll_count[job_id] = 0
        video.updated_at = datetime.now(UTC)
        return video, result

    async def get_status(self, job_id: str):
        video, result = self.store.resolve(job_id)
        count = self.store.poll_count[job_id]
        self.store.poll_count[job_id] += 1

        trigger_timeout = "timeout" in (video.original_filename or video.source_url or "")
        if trigger_timeout and count >= 1:
            video.status = "failed"
            result.status = "failed"
            result.error_message = "Analiz süresi zaman aşımına uğradı."
        elif count == 0:
            video.status = "processing"
            result.status = "running"
        else:
            video.status = "completed"
            result.status = "completed"
            result.is_fake = True
            result.confidence_score = 0.84
            result.fake_probability = 0.78
            result.real_probability = 0.22
            result.details = {
                "finalLabel": "fake",
                "llmExplanation": "Stub test aciklamasi.",
                "modalities": [
                    {"key": "visual", "label": "Gorsel", "score": 0.81, "confidence": 0.88, "verdict": "fake"},
                    {"key": "audio", "label": "Ses", "score": 0.67, "confidence": 0.79, "verdict": "fake"},
                    {"key": "text", "label": "Metin", "score": 0.42, "confidence": 0.65, "verdict": "uncertain"},
                ],
            }

        video.updated_at = datetime.now(UTC)
        return video, result

    async def get_result(self, job_id: str):
        return await self.get_status(job_id)

    def calculate_progress(self, video: FakeVideo) -> int:
        if video.status == "queued":
            return 20
        if video.status == "processing":
            return 65
        return 100

    def is_retryable(self, video: FakeVideo) -> bool:
        return video.status in {"failed", "expired"}


@pytest.fixture
def client():
    app = create_app(enable_lifespan=False)
    store = InMemoryAnalysisStore()

    def upload_override():
        return FakeUploadService(store)

    def analysis_override():
        return FakeAnalysisService(store)

    app.dependency_overrides[get_upload_service] = upload_override
    app.dependency_overrides[get_analysis_service] = analysis_override

    with TestClient(app) as test_client:
        yield test_client


def test_upload_video_returns_contract_fields(client: TestClient):
    response = client.post(
        "/upload-video",
        files={"file": ("sample.mp4", b"fake-video", "video/mp4")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert set(payload) >= {"jobId", "videoId", "status", "message", "sourceType"}
    assert payload["status"] == "queued"
    assert payload["filename"] == "sample.mp4"
    assert payload["sourceType"] == "file"


def test_upload_video_rejects_unsupported_type(client: TestClient):
    response = client.post(
        "/upload-video",
        files={"file": ("sample.txt", b"not-a-video", "text/plain")},
    )

    assert response.status_code == 415
    assert "Desteklenmeyen dosya tipi" in response.json()["detail"]


def test_upload_video_rejects_oversized_payload(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    original_limit = settings.max_file_size_mb
    monkeypatch.setattr(settings, "max_file_size_mb", 0)

    response = client.post(
        "/upload-video",
        files={"file": ("sample.mp4", b"too-large", "video/mp4")},
    )

    monkeypatch.setattr(settings, "max_file_size_mb", original_limit)

    assert response.status_code == 413
    assert "sınırını aşıyor" in response.json()["detail"]


def test_upload_url_rejects_invalid_platform_link(client: TestClient):
    response = client.post("/upload-video-url", json={"url": "https://example.com/video/123"})

    assert response.status_code == 422
    assert "Geçerli bir YouTube" in response.json()["detail"]


def test_upload_to_poll_to_result_flow(client: TestClient):
    upload_response = client.post(
        "/upload-video",
        files={"file": ("integration.mp4", b"video", "video/mp4")},
    )
    job_id = upload_response.json()["jobId"]

    first_status = client.get(f"/jobs/{job_id}")
    second_status = client.get(f"/jobs/{job_id}")
    result_response = client.get(f"/results/{job_id}")

    assert first_status.status_code == 200
    assert first_status.json()["status"] == "processing"
    assert second_status.status_code == 200
    assert second_status.json()["status"] == "completed"

    payload = result_response.json()
    assert result_response.status_code == 200
    assert payload["status"] == "completed"
    assert payload["finalScore"] == pytest.approx(0.78)
    assert len(payload["modalities"]) == 3
    assert payload["llmExplanation"] == "Stub test aciklamasi."


def test_timeout_and_retry_flow(client: TestClient):
    upload_response = client.post(
        "/upload-video",
        files={"file": ("timeout.mp4", b"video", "video/mp4")},
    )
    job_id = upload_response.json()["jobId"]

    client.get(f"/jobs/{job_id}")
    timeout_status = client.get(f"/jobs/{job_id}")
    result_response = client.get(f"/results/{job_id}")
    retry_response = client.post(f"/analyze/{job_id}", json={"retryFailed": True})

    assert timeout_status.status_code == 200
    assert timeout_status.json()["status"] == "failed"
    assert timeout_status.json()["retryable"] is True
    assert result_response.json()["errors"] == ["Analiz süresi zaman aşımına uğradı."]
    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "queued"
