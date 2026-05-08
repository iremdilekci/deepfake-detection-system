"""
VeraDeep API — FastAPI uygulama giriş noktası.

Endpoint grupları:
- /           → Sağlık kontrolü
- /upload-*   → Video yükleme (dosya veya URL)
- /analyze/*  → Analiz iş akışı
- /jobs/*     → Polling (iş durumu)
- /results/*  → Tamamlanmış analiz sonucu
- /audio-analysis/* → Ses modalitesi detayı (sprint görevi)
- /model-metrics    → SWAN-DF benchmark metrik tablosu (sprint görevi)
- /text/analyze     → NLP duygu analizi (sprint görevi)
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import Base, engine, get_db
from mappers.analysis_mapper import (
    to_result_response,
    to_status_response,
    to_upload_response,
)
from nlp.schemas import SentimentBatchRequest, SentimentBatchResponse

# torch/transformers opsiyonel — kurulu değilse NLP endpoint devre dışı kalır
try:
    from nlp.sentiment import SentimentAnalyzer, get_analyzer
    _NLP_AVAILABLE = True
except ImportError:
    _NLP_AVAILABLE = False
    SentimentAnalyzer = None  # type: ignore[assignment,misc]
    get_analyzer = None       # type: ignore[assignment]
from repositories.analysis_result_repository import AnalysisResultRepository
from repositories.video_repository import VideoRepository
from schemas.api_models import (
    AnalyzeRequest,
    JobStatusResponse,
    ModalityScore,
    ResultResponse,
    UploadAcceptedResponse,
    UrlUploadRequest,
)
from services.analysis_service import AnalysisService
from services.evaluation_service import EvaluationService
from services.file_storage_service import FileStorageService
from services.upload_service import UploadService
from services.upload_validation_service import UploadValidationService

# Modelleri yükle (Base.metadata'ya kaydolsunlar)
import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başlatılırken DB bağlantısını doğrula ve eksik tabloları oluştur."""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] Veritabani baglantisi dogrulandi.")
    yield
    await engine.dispose()
    print("[--] Veritabani baglantisi kapatildi.")


@asynccontextmanager
async def disabled_lifespan(app: FastAPI):
    yield

def get_upload_validator() -> UploadValidationService:
    return UploadValidationService()


def get_analysis_service(db: AsyncSession = Depends(get_db)) -> AnalysisService:
    video_repository = VideoRepository(db)
    result_repository = AnalysisResultRepository(db)
    return AnalysisService(
        video_repository=video_repository,
        result_repository=result_repository,
        timeout_seconds=settings.analysis_timeout_seconds,
    )


def get_upload_service(
    db: AsyncSession = Depends(get_db),
    validator: UploadValidationService = Depends(get_upload_validator),
) -> UploadService:
    video_repository = VideoRepository(db)
    result_repository = AnalysisResultRepository(db)
    analysis_service = AnalysisService(
        video_repository=video_repository,
        result_repository=result_repository,
        timeout_seconds=settings.analysis_timeout_seconds,
    )
    file_storage = FileStorageService(
        upload_dir=settings.upload_dir,
        validator=validator,
    )
    return UploadService(
        video_repository=video_repository,
        validator=validator,
        file_storage=file_storage,
        analysis_service=analysis_service,
    )


def create_app(enable_lifespan: bool = True) -> FastAPI:
    app = FastAPI(
        title="VeraDeep API",
        description="Multimodal deepfake detection backend",
        version="0.1.0",
        lifespan=lifespan if enable_lifespan else disabled_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["health"])
    async def health_check():
        return {"status": "ok", "service": "VeraDeep API"}

    @app.post(
        "/upload-video",
        response_model=UploadAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["upload"],
        summary="Multipart video yükle",
    )
    async def upload_video(
        file: UploadFile = File(...),
        upload_service: UploadService = Depends(get_upload_service),
    ):
        video = await upload_service.upload_file(file)
        return to_upload_response(video)

    @app.post(
        "/upload-video-url",
        response_model=UploadAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["upload"],
        summary="URL üzerinden video analizi",
    )
    async def upload_video_url(
        body: UrlUploadRequest,
        upload_service: UploadService = Depends(get_upload_service),
    ):
        video = await upload_service.upload_url(body.url)
        return to_upload_response(video)

    @app.post(
        "/analyze/{job_id}",
        response_model=UploadAcceptedResponse,
        tags=["analysis"],
        summary="Yuklenen icerik icin analizi yeniden siraya al",
    )
    async def analyze_job(
        job_id: str,
        body: AnalyzeRequest | None = None,
        analysis_service: AnalysisService = Depends(get_analysis_service),
    ):
        video, _ = await analysis_service.start_analysis(
            job_id=job_id,
            retry_failed=(body.retry_failed if body else False),
        )
        return to_upload_response(video)

    @app.get(
        "/jobs/{job_id}",
        response_model=JobStatusResponse,
        tags=["analysis"],
        summary="Analiz durumu ve polling bilgisi",
    )
    async def get_job_status(
        job_id: str,
        analysis_service: AnalysisService = Depends(get_analysis_service),
    ):
        video, _ = await analysis_service.get_status(job_id)
        return to_status_response(video, analysis_service)

    @app.get(
        "/results/{job_id}",
        response_model=ResultResponse,
        tags=["analysis"],
        summary="Analiz sonucunu getir",
    )
    async def get_result(
        job_id: str,
        analysis_service: AnalysisService = Depends(get_analysis_service),
    ):
        video, result = await analysis_service.get_result(job_id)
        return to_result_response(video, result)

    # ── Sprint Görevi 1: Ses analizi endpoint'i ──────────────────────────────
    @app.get(
        "/audio-analysis/{job_id}",
        response_model=ModalityScore | None,
        tags=["analysis"],
        summary="Ses modalitesi analiz sonucunu getir",
        description=(
            "Tamamlanmış bir analizden yalnızca ses (audio) modalitesini döndürür. "
            "Analiz henüz tamamlanmamışsa veya ses verisi yoksa 404 döner."
        ),
    )
    async def get_audio_analysis(
        job_id: str,
        analysis_service: AnalysisService = Depends(get_analysis_service),
    ):
        """
        /analyze/audio sprint görevinin karşılığı.
        Mevcut analiz sonucundan ses modalitesini filtreler ve döndürür.
        Gerçek ses modelinin Sprint 3'te entegre edilmesi planlanmaktadır.
        """
        video, result = await analysis_service.get_result(job_id)
        details = result.details or {}

        # Modalities listesinden audio kaydını bul
        audio_modality = next(
            (m for m in details.get("modalities", []) if m.get("key") == "audio"),
            None,
        )
        if not audio_modality:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bu iş için ses analizi verisi bulunamadı. Analiz tamamlanmamış olabilir.",
            )

        return ModalityScore.model_validate(audio_modality)

    # ── Sprint Görevi 5: SWAN-DF model metrikleri ────────────────────────────
    @app.get(
        "/model-metrics",
        response_model=dict[str, Any],
        tags=["evaluation"],
        summary="SWAN-DF benchmark metrik tablosu",
        description=(
            "Görsel, ses ve metin modellerinin Accuracy, Precision, Recall, F1-Score "
            "değerlerini döndürür. Frontend'deki MetricsTable bileşeni bu veriyi tüketir."
        ),
    )
    async def get_model_metrics():
        """
        SWAN-DF dataset üzerindeki benchmark metrikleri.
        Gerçek model eğitimi tamamlandığında bu değerler dinamik hale gelecek.
        """
        evaluation_service = EvaluationService()
        return evaluation_service.get_benchmark()

    # ── Sprint Görevi NLP: Metin duygu analizi ───────────────────────────────
    @app.post(
        "/text/analyze",
        response_model=SentimentBatchResponse,
        tags=["nlp"],
        summary="Metin listesi için duygu ve spam analizi",
        description=(
            "Verilen metin listesini Türkçe BERT modeli ile analiz eder. "
            "Her metin için sentiment etiketi, polarity ve fake_comment_score döner. "
            "Maksimum 50 metin desteklenir. "
            "torch/transformers kurulu değilse 503 döner."
        ),
    )
    async def analyze_text(body: SentimentBatchRequest):
        """
        NLP sprint görevi — savasy/bert-base-turkish-sentiment-cased modeli kullanır.
        Model ilk çağrıda Hugging Face'den indirilir ve bellekte önbelleğe alınır.
        torch kurulu değilse kurulum talimatı içeren hata döner.
        """
        if not _NLP_AVAILABLE or get_analyzer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "NLP modülü şu an kullanılamıyor. "
                    "torch ve transformers paketlerini yükleyin: "
                    "pip install torch transformers"
                ),
            )
        analyzer = get_analyzer()
        results = await run_in_threadpool(analyzer.analyze_batch, body.texts)
        return SentimentBatchResponse(results=results, total=len(results))

    return app


app = create_app()
