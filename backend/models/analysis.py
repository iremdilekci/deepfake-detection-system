"""
AnalysisResult (Analiz Sonuçları) modeli.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = (
        # Composite index: video bazında model sonuçlarını filtrele
        Index("ix_analysis_video_model", "video_id", "model_name"),
    )

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key ──
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Analizi yapılan video",
    )

    # ── Analiz Bilgileri ──
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Kullanılan AI modelin adı (örn: xception, efficientnet)",
    )
    is_fake: Mapped[bool | None] = mapped_column(
        nullable=True,
        comment="Model kararı: True=fake, False=gerçek, None=belirsiz",
    )
    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Güven skoru (0.0 – 1.0 arası)",
    )
    fake_probability: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Deepfake olma olasılığı (0.0 – 1.0)",
    )
    real_probability: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Gerçek olma olasılığı (0.0 – 1.0)",
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Frame bazlı skor dağılımı, heatmap meta vb.",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Analiz başarısız olursa hata mesajı",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
        comment="pending | running | completed | failed",
    )

    # ── Zaman Damgaları ──
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Analizin başladığı an",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Analizin tamamlandığı an",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── İlişkiler ──
    video: Mapped["Video"] = relationship(  # noqa: F821
        back_populates="analysis_results",
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult {self.model_name} fake={self.is_fake} conf={self.confidence_score}>"
