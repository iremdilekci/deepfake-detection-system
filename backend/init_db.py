"""
Uygulama başlatıldığında veritabanı tablolarını oluşturan yardımcı script.
Kullanım: python init_db.py
"""

import asyncio
from database import engine, Base

# Modelleri import ederek Base.metadata'ya kaydet
import models  # noqa: F401


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tüm tablolar başarıyla oluşturuldu!")
    print("   - users")
    print("   - videos")
    print("   - analysis_results")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init())
