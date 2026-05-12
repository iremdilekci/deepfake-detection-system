from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from models.video import Video
from schemas.api_models import JobStatus


class VideoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, video: Video) -> Video:
        self.session.add(video)
        await self.session.flush()
        await self.session.refresh(video)
        return video

    async def get(self, video_id: uuid.UUID) -> Video | None:
        return await self.session.get(Video, video_id)

    async def get_by_source_url(self, source_url: str) -> Video | None:
        from sqlalchemy import select
        stmt = select(Video).where(Video.source_url == source_url)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_status(self, video: Video, status: JobStatus) -> Video:
        video.status = status.value
        await self.session.flush()
        await self.session.refresh(video)
        return video
