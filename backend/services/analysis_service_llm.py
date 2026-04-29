from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from models.analysis import AnalysisResult
from models.video import Video
from repositories.analysis_result_repository import AnalysisResultRepository
from repositories.video_repository import VideoRepository
from schemas.api_models import JobStatus
from services.fusion_service import ModalityResult, run_fusion
from llm.prompt_builder import ModalityInput, FusionInput
from llm.llm_service import llm_service


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
        await self._populate_result(video, result)
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

    async def _populate_result(self, video: Video, result: AnalysisResult) -> None:
        # 1. Her modaliteden ham skor çıkar
        visual_score = self._extract_visual_features(video)
        audio_score = self._extract_audio_features(video)
        text_score, text_explanations = self._extract_text_features(video)

        # 2. fusion_service ile late fusion uygula
        modality_results = [
            ModalityResult(key="visual", score=visual_score, confidence=round(0.62 + abs(visual_score - 0.5), 3), available=True),
            ModalityResult(key="audio",  score=audio_score,  confidence=round(0.62 + abs(audio_score - 0.5), 3),  available=True),
            ModalityResult(key="text",   score=text_score,   confidence=round(0.62 + abs(text_score - 0.5), 3),   available=True),
        ]
        fusion = run_fusion(modality_results)

        final_score = fusion.final_score or 0.0
        final_label = fusion.final_label or "uncertain"
        is_fake = final_label == "fake"

        # 3. LLM açıklaması — Gemini API
        modality_inputs = [
            ModalityInput(
                key="visual", label="Görsel Analiz",
                score=visual_score, confidence=round(0.62 + abs(visual_score - 0.5), 3),
                verdict=self._score_to_verdict(visual_score),
                weight=fusion.weights.get("visual", 0.5), available=True,
            ),
            ModalityInput(
                key="audio", label="Ses Analizi",
                score=audio_score, confidence=round(0.62 + abs(audio_score - 0.5), 3),
                verdict=self._score_to_verdict(audio_score),
                weight=fusion.weights.get("audio", 0.3), available=True,
            ),
            ModalityInput(
                key="text", label="Metin Analizi",
                score=text_score, confidence=round(0.62 + abs(text_score - 0.5), 3),
                verdict=self._score_to_verdict(text_score),
                weight=fusion.weights.get("text", 0.2), available=True,
            ),
        ]
        fusion_input = FusionInput(
            final_score=final_score,
            final_label=final_label,
            confidence_note=fusion.confidence_note,
            errors=fusion.errors,
        )
        llm_explanation = await llm_service.generate_explanation(modality_inputs, fusion_input)

        # 4. Grafik verisi
        chart_data = self._generate_chart_data(video, visual_score, audio_score, text_score)

        # 5. Sonucu veritabanına yaz
        result.is_fake = is_fake
        result.confidence_score = round(0.71 + abs(final_score - 0.5), 3)
        result.fake_probability = final_score
        result.real_probability = round(1 - final_score, 3)
        result.details = {
            "videoScore":       visual_score,
            "audioScore":       audio_score,
            "textScore":        text_score,
            "finalLabel":       final_label,
            "fusionWeights":    fusion.weights,
            "confidenceNote":   fusion.confidence_note,
            "llmExplanation":   llm_explanation,
            "textExplanations": text_explanations,
            "errors":           fusion.errors,
            "modalities": [
                self._modality_payload("visual", "Gorsel Analiz", visual_score, fusion.weights.get("visual", 0.5)),
                self._modality_payload("audio",  "Ses Analizi",   audio_score,  fusion.weights.get("audio", 0.3)),
                self._modality_payload("text",   "Metin Analizi", text_score,   fusion.weights.get("text", 0.2)),
            ],
            "chartData": chart_data,
        }

    def _extract_visual_features(self, video: Video) -> float:
        """Video karelerinden görsel özellik çıkarımı. Gerçek model Sprint 3'te entegre edilecek."""
        base = ((video.id.int % 10_000) / 10_000)
        return round(min(0.95, 0.32 + base * 0.55), 3)

    def _extract_audio_features(self, video: Video) -> float:
        """Videodan ses özellik çıkarımı. Gerçek model Sprint 3'te entegre edilecek."""
        base = ((video.id.int % 10_000) / 10_000)
        return round(min(0.95, 0.24 + (1 - base) * 0.44), 3)

    def _extract_text_features(self, video: Video) -> tuple[float, list[str]]:
        """NLP tabanlı metin özellik çıkarımı."""
        from nlp.sentiment import get_analyzer
        analyzer = get_analyzer()

        mock_texts = [
            video.original_filename or "İsimsiz video",
            "Bu video kesinlikle sahte, yüz hatları çok garip duruyor linkte detaylar var.",
            "Harika bir paylaşım olmuş, teşekkürler!",
        ]

        nlp_results = analyzer.analyze_batch(mock_texts)
        if not nlp_results:
            base = ((video.id.int % 10_000) / 10_000)
            return round(min(0.95, 0.18 + ((base * 1.7) % 1) * 0.42), 3), ["Yeterli metin verisi bulunamadı."]

        avg_fake_score = sum(r.fake_comment_score for r in nlp_results) / len(nlp_results)
        text_explanations = list({exp for r in nlp_results for exp in r.explanations})
        return round(avg_fake_score, 3), text_explanations

    def _score_to_verdict(self, score: float) -> str:
        if score >= 0.65:
            return "fake"
        elif score < 0.35:
            return "real"
        return "uncertain"

    def _modality_payload(self, key: str, label: str, score: float, weight: float) -> dict:
        return {
            "key":        key,
            "label":      label,
            "score":      score,
            "confidence": round(0.62 + abs(score - 0.5), 3),
            "verdict":    self._score_to_verdict(score),
            "weight":     round(weight, 3),
            "available":  True,
        }

    def _generate_chart_data(self, video: Video, visual_base: float, audio_base: float, text_base: float) -> dict:
        """Zaman bazlı skor dağılımı. Gerçek frame analizi Sprint 3'te eklenecek."""
        import random
        duration = video.duration_seconds or 15.0

        labels, visual_data, audio_data, text_data = [], [], [], []
        for sec in range(int(duration) + 1):
            labels.append(f"{sec}s")
            visual_data.append(round(min(1.0, max(0.0, visual_base + random.uniform(-0.15, 0.15))) * 100, 1))
            audio_data.append(round(min(1.0, max(0.0, audio_base + random.uniform(-0.15, 0.15))) * 100, 1))
            text_data.append(round(min(1.0, max(0.0, text_base  + random.uniform(-0.10, 0.10))) * 100, 1))

        return {
            "labels": labels,
            "datasets": [
                {"label": "Gorsel Sinyal", "data": visual_data},
                {"label": "Ses Sinyali",   "data": audio_data},
                {"label": "Metin Sinyali", "data": text_data},
            ],
        }

    def _ensure_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)