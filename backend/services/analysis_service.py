"""
Analiz Servisi — Deepfake tespit iş akışının merkezi.

Sorumlulukları:
1. İş durumunu zamana göre ilerletir (queued → processing → completed).
2. Stub feature extraction ile modalite skorları üretir.
   (Gerçek CNN/audio modeli Sprint 3'te entegre edilecek.)
3. FusionService ile skorları ağırlıklı ortalamaya indirgir.
4. LLMService ile Gemini API'ye bağlanıp Türkçe açıklama üretir.
5. Zaman serisi grafik verisi oluşturur (Recharts için).
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from llm.llm_service import llm_service
from llm.prompt_builder import FusionInput, ModalityInput
from models.analysis import AnalysisResult
from models.video import Video
from repositories.analysis_result_repository import AnalysisResultRepository
from repositories.video_repository import VideoRepository
from schemas.api_models import JobStatus
from services.fusion_service import ModalityResult, run_fusion


class AnalysisService:
    # Sıradaki işin işlemeye başlaması için bekleme süresi
    queue_delay = timedelta(seconds=2)
    # İşleme tamamlanana kadar geçen süre
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

    async def start_analysis(
        self, job_id: str, retry_failed: bool = False
    ) -> tuple[Video, AnalysisResult]:
        """
        Analiz işini başlatır veya yeniden başlatır.

        Zaten devam eden / tamamlanmış işler için sync_state'e yönlendirir.
        Başarısız işler için retry_failed=True gerekmektedir.
        """
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

        # Durumu sıfırla ve yeniden kuyruğa al
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
        """İşin güncel durumunu senkronize ederek döndürür."""
        video = await self._get_video(job_id)
        result = await self._get_or_create_result(video)
        return await self.sync_state(video, result)

    async def get_result(self, job_id: str) -> tuple[Video, AnalysisResult]:
        """Sonuç sorgular — get_status ile aynı davranış."""
        return await self.get_status(job_id)

    async def sync_state(
        self, video: Video, result: AnalysisResult
    ) -> tuple[Video, AnalysisResult]:
        """
        Elapsed time'a bakarak işin durumunu ilerletir.

        Durum makinesi:
        - elapsed < 2s       → queued
        - 2s ≤ elapsed < 6s  → processing
        - elapsed ≥ 6s       → completed (sonuçlar üretilir)
        - elapsed ≥ timeout  → failed
        """
        now = datetime.now(UTC)
        created_at = self._ensure_utc(video.created_at)
        elapsed = now - created_at

        # Zaten terminal durumundaysa tekrar hesaplama
        if video.status in {
            JobStatus.completed.value,
            JobStatus.failed.value,
            JobStatus.expired.value,
        }:
            return video, result

        # Zaman aşımı kontrolü
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

        # Tamamlandı — sonuçları oluştur
        video.status = JobStatus.completed.value
        result.status = "completed"
        result.started_at = result.started_at or created_at + self.queue_delay
        result.completed_at = (
            result.completed_at
            or created_at + self.queue_delay + self.processing_delay
        )
        # Sonuçlar henüz oluşturulmadıysa üret (idempotent)
        if not result.details:
            await self._populate_result(video, result)
        await self.video_repository.session.flush()
        return video, result

    # ── Yardımcı Sorgular ────────────────────────────────────────────────────

    def calculate_progress(self, video: Video) -> int:
        """Kullanıcıya gösterilecek 0–100 ilerleme yüzdesini hesaplar."""
        job_status = JobStatus(video.status)
        if job_status in {JobStatus.completed, JobStatus.failed, JobStatus.expired}:
            return 100

        created_at = self._ensure_utc(video.created_at)
        elapsed = max(0.0, (datetime.now(UTC) - created_at).total_seconds())

        if job_status == JobStatus.queued:
            return min(35, 15 + int(elapsed * 10))
        if job_status == JobStatus.processing:
            return min(95, 45 + int((elapsed - self.queue_delay.total_seconds()) * 12))
        return 10

    def is_retryable(self, video: Video) -> bool:
        """Başarısız veya süresi dolmuş işleri yeniden denemek mümkün mü?"""
        return video.status in {JobStatus.failed.value, JobStatus.expired.value}

    # ── Sonuç Üretimi ────────────────────────────────────────────────────────

    async def _populate_result(self, video: Video, result: AnalysisResult) -> None:
        """
        Analiz sonuçlarını hesaplar ve result.details'e yazar.

        Adımlar:
        1. Stub feature extraction (görsel, ses, metin skorları)
        2. Late fusion ile final_score ve final_label
        3. Gemini LLM ile Türkçe açıklama
        4. Recharts için zaman serisi grafik verisi
        """
        # 1. Stub feature extraction
        # Gerçek CNN ve audio modeli Sprint 3'te buralara bağlanacak
        visual_score = self._extract_visual_features(video)
        audio_score = self._extract_audio_features(video)
        text_score = self._extract_text_features(video)

        # 2. Late fusion — eksik modalite ve düşük güven durumlarını yönetir
        modality_results = [
            ModalityResult(
                key="visual",
                score=visual_score,
                confidence=round(0.62 + abs(visual_score - 0.5), 3),
                available=True,
            ),
            ModalityResult(
                key="audio",
                score=audio_score,
                confidence=round(0.62 + abs(audio_score - 0.5), 3),
                available=True,
            ),
            ModalityResult(
                key="text",
                score=text_score,
                confidence=round(0.62 + abs(text_score - 0.5), 3),
                available=True,
            ),
        ]
        fusion = run_fusion(modality_results)

        final_score = fusion.final_score or 0.0
        final_label = fusion.final_label or "uncertain"
        is_fake = final_label == "fake"

        # 3. LLM açıklaması — Gemini API (key yoksa fallback metin döner)
        modality_inputs = [
            ModalityInput(
                key="visual",
                label="Görsel Analiz",
                score=visual_score,
                confidence=round(0.62 + abs(visual_score - 0.5), 3),
                verdict=self._score_to_verdict(visual_score),
                weight=fusion.weights.get("visual", 0.5),
                available=True,
            ),
            ModalityInput(
                key="audio",
                label="Ses Analizi",
                score=audio_score,
                confidence=round(0.62 + abs(audio_score - 0.5), 3),
                verdict=self._score_to_verdict(audio_score),
                weight=fusion.weights.get("audio", 0.3),
                available=True,
            ),
            ModalityInput(
                key="text",
                label="Metin Analizi",
                score=text_score,
                confidence=round(0.62 + abs(text_score - 0.5), 3),
                verdict=self._score_to_verdict(text_score),
                weight=fusion.weights.get("text", 0.2),
                available=True,
            ),
        ]
        fusion_input = FusionInput(
            final_score=final_score,
            final_label=final_label,
            confidence_note=fusion.confidence_note,
            errors=fusion.errors,
        )
        llm_explanation = await llm_service.generate_explanation(
            modality_inputs, fusion_input
        )

        # 4. Recharts için zaman serisi grafik verisi
        chart_data = self._generate_chart_data(
            video, visual_score, audio_score, text_score
        )

        # 5. Veritabanına yaz
        result.is_fake = is_fake
        result.confidence_score = round(0.71 + abs(final_score - 0.5), 3)
        result.fake_probability = final_score
        result.real_probability = round(1 - final_score, 3)
        result.details = {
            "finalLabel":      final_label,
            "fusionWeights":   fusion.weights,
            "llmExplanation":  llm_explanation,
            "errors":          fusion.errors,
            "modalities": [
                self._modality_payload(
                    "visual", "Gorsel Analiz", visual_score,
                    fusion.weights.get("visual", 0.5),
                ),
                self._modality_payload(
                    "audio", "Ses Analizi", audio_score,
                    fusion.weights.get("audio", 0.3),
                ),
                self._modality_payload(
                    "text", "Metin Analizi", text_score,
                    fusion.weights.get("text", 0.2),
                ),
            ],
            "chartData": chart_data,
        }

    # ── Feature Extraction (Stub) ────────────────────────────────────────────

    def _extract_visual_features(self, video: Video) -> float:
        """
        Video karelerinden görsel deepfake skoru çıkarır.
        Gerçek model (Xception / EfficientNet) Sprint 3'te entegre edilecek.
        Şu an video UUID'sinden deterministik stub skor üretir.
        """
        base = (video.id.int % 10_000) / 10_000
        return round(min(0.95, 0.32 + base * 0.55), 3)

    def _extract_audio_features(self, video: Video) -> float:
        """
        Videodan ses deepfake skoru çıkarır.
        Gerçek model (MFCC + CNN / RawNet) Sprint 3'te entegre edilecek.
        Şu an video UUID'sinden deterministik stub skor üretir.
        """
        base = (video.id.int % 10_000) / 10_000
        return round(min(0.95, 0.24 + (1 - base) * 0.44), 3)

    def _extract_text_features(self, video: Video) -> float:
        """
        Metin/NLP tabanlı deepfake skoru çıkarır.
        Gerçek veri: video başlığı, yorumlar vb. (Sprint 3'te).
        Şu an video UUID'sinden deterministik stub skor üretir.
        """
        base = (video.id.int % 10_000) / 10_000
        return round(min(0.95, 0.18 + ((base * 1.7) % 1) * 0.42), 3)

    # ── Chart Data ───────────────────────────────────────────────────────────

    def _generate_chart_data(
        self,
        video: Video,
        visual_base: float,
        audio_base: float,
        text_base: float,
    ) -> dict:
        """
        Recharts bileşenine beslenecek zaman serisi grafik verisi üretir.

        Her saniye için görsel/ses/metin skorunu küçük rastgele sapma ile
        simüle eder. Gerçek frame-level analiz Sprint 3'te eklenecek.

        Returns:
            { labels: ["0s", ...], datasets: [{label, data}, ...] }
        """
        duration = video.duration_seconds or 15.0
        labels, visual_data, audio_data, text_data = [], [], [], []

        for sec in range(int(duration) + 1):
            labels.append(f"{sec}s")
            # Her saniyede küçük rastgele sapma — gerçekçi görünüm sağlar
            visual_data.append(
                round(min(100.0, max(0.0, visual_base * 100 + random.uniform(-15, 15))), 1)
            )
            audio_data.append(
                round(min(100.0, max(0.0, audio_base * 100 + random.uniform(-15, 15))), 1)
            )
            text_data.append(
                round(min(100.0, max(0.0, text_base * 100 + random.uniform(-10, 10))), 1)
            )

        return {
            "labels": labels,
            "datasets": [
                {"label": "Gorsel Sinyal", "data": visual_data},
                {"label": "Ses Sinyali",   "data": audio_data},
                {"label": "Metin Sinyali", "data": text_data},
            ],
        }

    # ── Yardımcı Metodlar ────────────────────────────────────────────────────

    def _score_to_verdict(self, score: float) -> str:
        """0–1 skoru "fake" | "uncertain" | "real" etiketine dönüştürür."""
        if score >= 0.65:
            return "fake"
        if score < 0.35:
            return "real"
        return "uncertain"

    def _modality_payload(
        self, key: str, label: str, score: float, weight: float
    ) -> dict:
        """Tek bir modalite için API yanıt bloğunu oluşturur."""
        return {
            "key":        key,
            "label":      label,
            "score":      score,
            "confidence": round(0.62 + abs(score - 0.5), 3),
            "verdict":    self._score_to_verdict(score),
            "weight":     round(weight, 3),
            "available":  True,
        }

    async def _get_video(self, job_id: str) -> Video:
        """Job ID'yi UUID'ye dönüştürür ve veritabanından videoyu çeker."""
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
        """Video için analiz sonucu kaydı varsa çeker, yoksa oluşturur."""
        result = await self.result_repository.get_by_video_id(video.id)
        if result is not None:
            return result

        result = AnalysisResult(
            video_id=video.id,
            model_name="multimodal_stub",
            status="pending",
        )
        return await self.result_repository.add(result)

    def _ensure_utc(self, value: datetime) -> datetime:
        """Timezone bilgisi eksik datetime'ları UTC olarak işaretler."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
