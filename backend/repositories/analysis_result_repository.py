from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.analysis import AnalysisResult


class AnalysisResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, result: AnalysisResult) -> AnalysisResult:
        self.session.add(result)
        await self.session.flush()
        await self.session.refresh(result)
        return result

    async def get_by_video_id(self, video_id: uuid.UUID) -> AnalysisResult | None:
        statement = (
            select(AnalysisResult)
            .where(AnalysisResult.video_id == video_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
