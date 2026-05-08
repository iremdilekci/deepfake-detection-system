"""
SWAN-DF Evaluation Pipeline modeli.
Tahmin (prediction), ground truth etiketi ve değerlendirme metriklerini saklar.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        Index("ix_evaluation_results_video_model", "video_id", "model_version"),
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
        comment="Değerlendirilen video",
    )

    # ── Evaluation Bilgileri ──
    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Değerlendirmede kullanılan SWAN-DF model versiyonu",
    )
    
    ground_truth_label: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Gerçek etiket (ör: 'fake', 'real')",
    )
    
    prediction_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Modelin ürettiği deepfake olasılık skoru (0-1 arası)",
    )
    
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Tahminin doğru olup olmadığı",
    )

    metrics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Ek metrikler (accuracy, f1-score, latency vb.)",
    )

    # ── Zaman Damgaları ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── İlişkiler ──
    video: Mapped["Video"] = relationship(  # noqa: F821
        # Video modeli tarafında 'evaluation_results' ilişkisi eklenebilir.
        backref="evaluation_results",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<EvaluationResult {self.id} video={self.video_id} correct={self.is_correct}>"
