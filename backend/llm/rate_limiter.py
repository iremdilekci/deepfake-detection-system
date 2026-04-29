from __future__ import annotations

import time
import asyncio
import logging
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    LLM API çağrıları için sliding window rate limiter.

    Parametreler:
    - max_requests: Zaman penceresi içinde izin verilen maksimum istek sayısı
    - window_seconds: Zaman penceresi süresi (saniye)

    Kullanım:
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        await limiter.acquire()  # İstek hakkı bekle
        # API çağrısı yap
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        İstek hakkı bekler.
        Pencere doluysa otomatik olarak bekler.
        """
        async with self._lock:
            now = time.monotonic()

            # Pencere dışındaki eski istekleri temizle
            while self._timestamps and self._timestamps[0] < now - self.window_seconds:
                self._timestamps.popleft()

            # Pencere doluysa bekle
            if len(self._timestamps) >= self.max_requests:
                oldest = self._timestamps[0]
                wait_time = self.window_seconds - (now - oldest) + 0.1
                if wait_time > 0:
                    logger.warning(
                        "Rate limit: %d/%d istek kullanıldı. %.1f saniye bekleniyor.",
                        len(self._timestamps), self.max_requests, wait_time,
                    )
                    await asyncio.sleep(wait_time)

            self._timestamps.append(time.monotonic())

    @property
    def remaining(self) -> int:
        """Kalan istek hakkı."""
        now = time.monotonic()
        active = sum(1 for t in self._timestamps if t >= now - self.window_seconds)
        return max(0, self.max_requests - active)


# Gemini ücretsiz tier: dakikada 15 istek
gemini_limiter = RateLimiter(max_requests=12, window_seconds=60.0)