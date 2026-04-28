from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from models.analysis import AnalysisResult
from models.video import Video
from repositories.analysis_result_repository import AnalysisResultRepository
from repositories.video_repository import VideoRepository
from schemas.api_models import JobStatus


class AnalysisService:
    queue_delay = timedelta(seconds=2)
    processing_delay = timedelta(seconds=4)

    def __init__(
        self,
        video_repository: VideoRepository,
        result_repository: AnalysisResultRepository,
        timeout_seconds: int = 90,
    ) -> None:
        self.video_repository = video_repository
        self.result_repository = result_repository
        self.timeout_seconds = timeout_seconds

    async def start_analysis(self, job_id: str, retry_failed: bool = False) -> tuple[Video, AnalysisResult]:
        video = await self._get_video(job_id)
        result = await self._get_or_create_result(video)

        if video.status == JobStatus.failed.value and not retry_failed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Başarısız iş yeniden başlatılmak isteniyorsa retryFailed=true gönderin.",
            )

        if video.status in {
            JobStatus.queued.value,
            JobStatus.processing.value,
            JobStatus.completed.value,
        }:
            return await self.sync_state(video, result)

        # Stub analiz akışı gerçek worker gelene kadar burada tutuluyor.
        video.status = JobStatus.queued.value
        result.status = "pending"
        result.started_at = None
        result.completed_at = None
        result.error_message = None
        result.is_fake = None
        result.confidence_score = None
        result.fake_probability = None
        result.real_probability = None
        result.details = None
        await self.video_repository.session.flush()
        return await self.sync_state(video, result)

    async def get_status(self, job_id: str) -> tuple[Video, AnalysisResult]:
        video = await self._get_video(job_id)
        result = await self._get_or_create_result(video)
        return await self.sync_state(video, result)

    async def get_result(self, job_id: str) -> tuple[Video, AnalysisResult]:
        return await self.get_status(job_id)

    async def sync_state(self, video: Video, result: AnalysisResult) -> tuple[Video, AnalysisResult]:
        now = datetime.now(UTC)
        created_at = self._ensure_utc(video.created_at)
        elapsed = now - created_at

        if video.status in {JobStatus.completed.value, JobStatus.failed.value, JobStatus.expired.value}:
            return video, result

        if elapsed.total_seconds() >= self.timeout_seconds:
            video.status = JobStatus.failed.value
            result.status = "failed"
            result.error_message = "Analiz süresi zaman aşımına uğradı."
            result.completed_at = now
            await self.video_repository.session.flush()
            return video, result

        if elapsed < self.queue_delay:
            video.status = JobStatus.queued.value
            result.status = "pending"
            await self.video_repository.session.flush()
            return video, result

        if elapsed < self.queue_delay + self.processing_delay:
            video.status = JobStatus.processing.value
            result.status = "running"
            result.started_at = result.started_at or created_at + self.queue_delay
            await self.video_repository.session.flush()
            return video, result

        video.status = JobStatus.completed.value
        result.status = "completed"
        result.started_at = result.started_at or created_at + self.queue_delay
        result.completed_at = result.completed_at or created_at + self.queue_delay + self.processing_delay
        self._populate_stub_result(video, result)
        await self.video_repository.session.flush()
        return video, result

    async def _get_video(self, job_id: str) -> Video:
        try:
            video_id = uuid.UUID(job_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="İlgili analiz işi bulunamadı.",
            ) from exc

        video = await self.video_repository.get(video_id)
        if video is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="İlgili analiz işi bulunamadı.",
            )
        return video

    async def _get_or_create_result(self, video: Video) -> AnalysisResult:
        result = await self.result_repository.get_by_video_id(video.id)
        if result is not None:
            return result

        result = AnalysisResult(
            video_id=video.id,
            model_name="multimodal_stub",
            status="pending",
        )
        return await self.result_repository.add(result)

    def calculate_progress(self, video: Video) -> int:
        status_value = JobStatus(video.status)
        if status_value in {JobStatus.completed, JobStatus.failed, JobStatus.expired}:
            return 100

        created_at = self._ensure_utc(video.created_at)
        elapsed = max(0.0, (datetime.now(UTC) - created_at).total_seconds())
        if status_value == JobStatus.queued:
            return min(35, 15 + int(elapsed * 10))
        if status_value == JobStatus.processing:
            return min(95, 45 + int((elapsed - self.queue_delay.total_seconds()) * 12))
        return 10

    def is_retryable(self, video: Video) -> bool:
        return video.status in {JobStatus.failed.value, JobStatus.expired.value}

    def _populate_stub_result(self, video: Video, result: AnalysisResult) -> None:
        # Özellik Çıkarımı (Feature Extraction)
        visual_score = self._extract_visual_features(video)
        audio_score = self._extract_audio_features(video)
        text_score, text_explanations = self._extract_text_features(video)
        
        # Skor Normalizasyonu ve Birleştirme (Score Normalization)
        final_score = self._normalize_and_combine_scores(visual_score, audio_score, text_score)
        
        # Grafik (Chart.js) verisinin hazırlanması
        chart_data = self._generate_chart_data(video, visual_score, audio_score, text_score)
        
        is_fake = final_score >= 0.5

        result.is_fake = is_fake
        result.confidence_score = round(0.71 + abs(final_score - 0.5), 3)
        result.fake_probability = final_score
        result.real_probability = round(1 - final_score, 3)
        result.details = {
            "finalLabel": "fake" if is_fake else "real",
            "llmExplanation": self._build_llm_explanation(is_fake, visual_score, audio_score, text_score),
            "textExplanations": text_explanations,
            "modalities": [
                self._modality_payload("visual", "Gorsel", visual_score),
                self._modality_payload("audio", "Ses", audio_score),
                self._modality_payload("text", "Metin", text_score),
            ],
            "chartData": chart_data,
        }

    def _extract_visual_features(self, video: Video) -> float:
        """Video karelerinden (frame) görsel özellik çıkarımı ve skorlaması."""
        base = ((video.id.int % 10_000) / 10_000)
        return round(min(0.95, 0.32 + base * 0.55), 3)

    def _extract_audio_features(self, video: Video) -> float:
        """Videodan işitsel (ses) özellik çıkarımı ve skorlaması."""
        base = ((video.id.int % 10_000) / 10_000)
        return round(min(0.95, 0.24 + (1 - base) * 0.44), 3)

    def _extract_text_features(self, video: Video) -> tuple[float, list[str]]:
        """NLP tabanlı metin özellik çıkarımı ve skorlaması."""
        from nlp.sentiment import get_analyzer
        analyzer = get_analyzer()
        
        mock_texts = [
            video.original_filename or "İsimsiz video",
            "Bu video kesinlikle sahte, yüz hatları çok garip duruyor linkte detaylar var.",
            "Harika bir paylaşım olmuş, teşekkürler!"
        ]
        
        nlp_results = analyzer.analyze_batch(mock_texts)
        if not nlp_results:
            base = ((video.id.int % 10_000) / 10_000)
            return round(min(0.95, 0.18 + ((base * 1.7) % 1) * 0.42), 3), ["Yeterli metin verisi bulunamadı."]
            
        avg_fake_score = sum(r.fake_comment_score for r in nlp_results) / len(nlp_results)
        
        text_explanations = []
        for r in nlp_results:
            text_explanations.extend(r.explanations)
        text_explanations = list(set(text_explanations))
        
        return round(avg_fake_score, 3), text_explanations

    def _normalize_and_combine_scores(self, visual_score: float, audio_score: float, text_score: float) -> float:
        """Modellerden gelen bağımsız skorları ağırlıklandırarak (weighted fusion) normalize eder."""
        w_visual = 0.45
        w_audio = 0.35
        w_text = 0.20
        
        # Gelecekte min-max scaler veya sigmoid normalizasyonu da eklenebilir
        final_score = (visual_score * w_visual) + (audio_score * w_audio) + (text_score * w_text)
        return round(final_score, 3)

    def _build_llm_explanation(
        self,
        is_fake: bool,
        visual_score: float,
        audio_score: float,
        text_score: float,
    ) -> str:
        verdict = "sahte olma ihtimalini" if is_fake else "gercek olma ihtimalini"
        return (
            "Stub analiz ozeti: sistem gorsel, ses ve metin sinyallerini birlikte "
            f"degerlendirerek icerigin {verdict} daha yuksek buldu. "
            f"Gorsel skor {visual_score:.2f}, ses skor {audio_score:.2f}, metin skor {text_score:.2f}."
        )

    def _modality_payload(self, key: str, label: str, score: float) -> dict[str, str | float]:
        if score >= 0.6:
            verdict = "fake"
        elif score <= 0.4:
            verdict = "real"
        else:
            verdict = "uncertain"

        return {
            "key": key,
            "label": label,
            "score": score,
            "confidence": round(0.62 + abs(score - 0.5), 3),
            "verdict": verdict,
        }

    def _generate_chart_data(self, video: Video, visual_base: float, audio_base: float, text_base: float) -> dict:
        """Video süresi boyunca frame/zaman bazlı skor dağılımını (Dataset/Labels) simüle eder."""
        import random
        duration = video.duration_seconds or 15.0
        
        labels = []
        visual_data = []
        audio_data = []
        text_data = []
        
        # Her 1 saniyede bir veri noktası
        for sec in range(int(duration) + 1):
            labels.append(f"{sec}s")
            
            # Base skorlar etrafında küçük dalgalanmalar yaratıyoruz
            v_val = min(1.0, max(0.0, visual_base + random.uniform(-0.15, 0.15)))
            a_val = min(1.0, max(0.0, audio_base + random.uniform(-0.15, 0.15)))
            t_val = min(1.0, max(0.0, text_base + random.uniform(-0.10, 0.10)))
            
            visual_data.append(round(v_val * 100, 1))
            audio_data.append(round(a_val * 100, 1))
            text_data.append(round(t_val * 100, 1))
            
        return {
            "labels": labels,
            "datasets": [
                {"label": "Gorsel Sinyal", "data": visual_data},
                {"label": "Ses Sinyali", "data": audio_data},
                {"label": "Metin Sinyali", "data": text_data}
            ]
        }

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
