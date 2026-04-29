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
    """
    Tek bir modaliteye ait ham skor bloğu.

    Alanlar:
    - key:        Modalite kimliği. "visual" | "audio" | "text"
    - label:      Kullanıcıya gösterilecek Türkçe isim. Örn: "Görsel Analiz"
    - score:      0–1 arası normalize deepfake olasılığı.
                  1.0 → kesinlikle sahte, 0.0 → kesinlikle gerçek.
    - confidence: Modelin bu skora olan güveni. 0–1 arası.
                  Düşük güven → skorun ağırlığı fusion'da azaltılır.
    - verdict:    İnsan okunabilir karar etiketi.
                  "fake"      → score >= 0.65
                  "uncertain" → 0.35 <= score < 0.65
                  "real"      → score < 0.35
    - weight:     Fusion'da bu modaliteye atanan ağırlık (0–1 arası, toplamı 1.0).
                  Eksik modalitede 0.0 olur, diğerleri yeniden normalize edilir.
    - available:  Bu modalite analizinin başarıyla tamamlanıp tamamlanmadığı.
                  False ise score ve confidence alanları None olabilir.
    """
    key: Literal["visual", "audio", "text"]
    label: str
    score: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    verdict: Literal["fake", "real", "uncertain"] | None = None
    weight: float = Field(default=0.0, ge=0, le=1)
    available: bool = True


class VideoMeta(ApiModel):
    """
    Analiz edilen videonun meta verisi.

    Alanlar:
    - filename:         Orijinal dosya adı. URL kaynağında None olabilir.
    - source_type:      "file" → doğrudan yükleme, "url" → link analizi.
    - source_url:       Kaynak URL. Dosya yüklemesinde None.
    - mime_type:        Video MIME tipi. Örn: "video/mp4"
    - file_size_bytes:  Dosya boyutu bayt cinsinden.
    - duration_seconds: Video süresi saniye cinsinden. İşlenemezse None.
    """
    filename: str | None = None
    source_type: SourceType
    source_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None


class ChartDataset(ApiModel):
    """
    Tek bir grafik veri serisi.

    Alanlar:
    - label: Grafik efsanesinde gösterilecek isim. Örn: "Deepfake Olasılığı"
    - data:  Her zaman dilimine karşılık gelen 0–100 arası yüzde değerleri.
    """
    label: str
    data: list[float]


class ChartData(ApiModel):
    """
    Frontend Chart.js bileşenine doğrudan beslenecek grafik verisi.

    Alanlar:
    - labels:   X ekseni etiketleri. Zaman damgaları. Örn: ["0s", "1s", "2s"]
    - datasets: Her modalite için bir dataset. Sıra: [visual, audio, text]
    """
    labels: list[str]
    datasets: list[ChartDataset]


class LLMExplanation(ApiModel):
    """
    LLM katmanının ürettiği açıklanabilir AI çıktısı.

    Alanlar:
    - summary:        Kısa özet. Kullanıcıya gösterilecek ana metin. Maks 3 cümle.
    - reasoning:      Modalite bazlı gerekçe. Her modalite için 1 cümle açıklama.
    - confidence_note: Genel güven düzeyi hakkında uyarı. Düşük güvende doldurulur.
    - model_used:     Açıklamayı üreten LLM modeli. Örn: "claude-sonnet-4-20250514"
    - generated_at:   Açıklamanın üretildiği zaman damgası.
    """
    summary: str
    reasoning: dict[str, str] = Field(default_factory=dict)
    confidence_note: str | None = None
    model_used: str | None = None
    generated_at: datetime | None = None


class ResultResponse(ApiModel):
    """
    Analiz tamamlandığında dönen tam sonuç nesnesi.

    Skor alanları:
    - video_score:  Görsel modalite ham skoru. 0–1. Modalite yoksa None.
    - audio_score:  Ses modalite ham skoru. 0–1. Modalite yoksa None.
    - text_score:   Metin modalite ham skoru. 0–1. Modalite yoksa None.
    - final_score:  Ağırlıklı fusion skoru. Mevcut modalitelerin weighted average'ı.
                    Hiçbir modalite yoksa None.
    - final_label:  Final karar etiketi.
                    "fake"      → final_score >= 0.65
                    "uncertain" → 0.35 <= final_score < 0.65
                    "real"      → final_score < 0.35
                    None        → analiz başarısız veya henüz tamamlanmadı.

    Diğer alanlar:
    - job_id:            İşin benzersiz kimliği.
    - video_id:          Videonun benzersiz kimliği.
    - status:            İşin güncel durumu.
    - modalities:        Her modaliteye ait detaylı skor bloğu.
    - llm_explanation:   Ham LLM açıklama metni (geriye dönük uyumluluk için).
    - llm_detail:        Yapılandırılmış LLM açıklama nesnesi.
    - text_explanations: NLP modülünden gelen ham açıklama listesi.
    - chart_data:        Zaman serisi grafik verisi.
    - video_meta:        Video meta verisi.
    - errors:            İşlem sırasında oluşan hata mesajları listesi.
    - updated_at:        Son güncelleme zaman damgası.
    """
    job_id: str
    video_id: str
    status: JobStatus

    # Modalite bazlı ham skorlar (fusion öncesi)
    video_score: float | None = Field(default=None, ge=0, le=1)
    audio_score: float | None = Field(default=None, ge=0, le=1)
    text_score: float | None = Field(default=None, ge=0, le=1)

    # Fusion sonrası final skor
    final_score: float | None = Field(default=None, ge=0, le=1)
    final_label: Literal["fake", "real", "uncertain"] | None = None

    # LLM açıklaması
    llm_explanation: str | None = None          # Ham metin (frontend uyumluluğu)
    llm_detail: LLMExplanation | None = None    # Yapılandırılmış detay

    # Modalite detayları
    text_explanations: list[str] = Field(default_factory=list)
    modalities: list[ModalityScore] = Field(default_factory=list)

    # Grafik ve meta
    chart_data: ChartData | None = None
    video_meta: VideoMeta

    # Hata ve zaman
    errors: list[str] = Field(default_factory=list)
    updated_at: datetime