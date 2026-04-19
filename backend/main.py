from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, UploadFile, status
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
from repositories.analysis_result_repository import AnalysisResultRepository
from repositories.video_repository import VideoRepository
from schemas.api_models import (
    AnalyzeRequest,
    JobStatusResponse,
    ResultResponse,
    UploadAcceptedResponse,
    UrlUploadRequest,
)
from services.analysis_service import AnalysisService
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
    print("✅ Veritabanı bağlantısı doğrulandı.")
    yield
    await engine.dispose()
    print("🔌 Veritabanı bağlantısı kapatıldı.")


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

    return app


app = create_app()
