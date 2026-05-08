"""
Veritabanı motoru ve oturum fabrikası.
Async SQLAlchemy 2.0 kullanılmaktadır.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(
    settings.db_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Tüm modellerin miras aldığı temel sınıf."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI Depends ile kullanılacak oturum jeneratörü."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
