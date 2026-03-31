"""
NLP çıktıları için Pydantic şemaları.
FastAPI endpoint'lerinde doğrudan response_model olarak kullanılabilir.
"""

from pydantic import BaseModel, Field


class SentimentResult(BaseModel):
    """Tek bir metin için duygu analizi sonucu."""

    text: str = Field(
        ...,
        description="Analiz edilen orijinal metin",
        json_schema_extra={"example": "Bu video çok şüpheli görünüyor"},
    )
    cleaned_text: str = Field(
        ...,
        description="Ön işlemeden geçirilmiş temiz metin",
        json_schema_extra={"example": "Bu video çok şüpheli görünüyor"},
    )
    sentiment_label: str = Field(
        ...,
        description="Duygu etiketi: positive, negative veya neutral",
        json_schema_extra={"example": "negative"},
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Modelin tahmin güven skoru (0.0 – 1.0)",
        json_schema_extra={"example": 0.92},
    )


class SentimentBatchRequest(BaseModel):
    """Toplu analiz isteği."""

    texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Analiz edilecek metin listesi (maks 50)",
    )


class SentimentBatchResponse(BaseModel):
    """Toplu analiz yanıtı."""

    results: list[SentimentResult]
    total: int = Field(..., description="Analiz edilen toplam metin sayısı")
