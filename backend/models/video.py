"""
Video modeli.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        # Composite index: belirli bir kullanıcının videolarını tarihe göre sıralama
        Index("ix_videos_owner_created", "owner_id", "created_at"),
    )

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ── Foreign Key ──
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Videoyu yükleyen kullanıcı",
    )

    # ── Video Bilgileri ──
    original_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Yüklenen dosyanın orijinal adı",
    )
    stored_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Diskte saklanan dosya adı (UUID tabanlı)",
    )
    source_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="URL üzerinden yüklenmişse kaynak adresi",
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Dosya boyutu (byte)",
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="video/mp4, video/webm vb.",
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="Video süresi (saniye)",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
        comment="pending | processing | completed | failed",
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
    owner: Mapped["User"] = relationship(  # noqa: F821
        back_populates="videos",
    )
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(  # noqa: F821
        back_populates="video",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Video {self.id} status={self.status}>"
