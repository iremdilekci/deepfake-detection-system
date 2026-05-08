from __future__ import annotations

import asyncio
import logging
from google import genai

from config import settings
from llm.prompt_builder import ModalityInput, FusionInput, build_user_prompt, SYSTEM_PROMPT
from llm.rate_limiter import gemini_limiter

logger = logging.getLogger(__name__)

# Servis katmanı sabitleri
TIMEOUT_SECONDS = 30       # Tek API çağrısı için maksimum süre
MAX_RETRIES = 2            # Geçici hatalarda yeniden deneme sayısı
RETRY_DELAY_SECONDS = 2.0  # Yeniden denemeler arası bekleme süresi


class LLMService:
    """
    Google Gemini API ile iletişim kuran servis katmanı.

    Özellikler:
    - Timeout: Her çağrı maksimum TIMEOUT_SECONDS süre bekler
    - Retry: Geçici hatalarda MAX_RETRIES kez yeniden dener
    - Rate limit: Dakikada maksimum 12 istek (Gemini ücretsiz tier)
    - Fallback: Tüm denemeler başarısız olursa stub metin döner
    """

    MODEL = "gemini-2.0-flash-lite"

    def __init__(self) -> None:
        if settings.gemini_api_key:
            self.client = genai.Client(api_key=settings.gemini_api_key)
        else:
            self.client = None

    async def generate_explanation(
        self,
        modalities: list[ModalityInput],
        fusion: FusionInput,
    ) -> str:
        """
        Modalite skorları ve fusion sonucuna göre LLM açıklaması üretir.

        Parametreler:
        - modalities: Her modaliteye ait skor bilgisi
        - fusion: Late fusion sonucu

        Döndürür:
        - str: Gemini tarafından üretilen Türkçe açıklama metni
               Tüm denemeler başarısız olursa fallback metin döner.
        """
        if not self.client:
            logger.warning("GEMINI_API_KEY tanımlı değil. Fallback metin döndürülüyor.")
            return self._fallback_explanation(fusion)

        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(modalities, fusion)
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 2):  # 1, 2, 3
            try:
                # Rate limit kontrolü
                await gemini_limiter.acquire()

                # Timeout ile API çağrısı
                explanation = await asyncio.wait_for(
                    self._call_api(prompt),
                    timeout=TIMEOUT_SECONDS,
                )

                if not explanation or not explanation.strip():
                    return self._fallback_explanation(fusion)

                logger.info("LLM açıklaması üretildi (deneme %d).", attempt)
                return explanation.strip()

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(f"API timeout ({TIMEOUT_SECONDS}s)")
                logger.warning("LLM timeout (deneme %d/%d).", attempt, MAX_RETRIES + 1)

            except Exception as exc:
                last_error = exc
                logger.warning("LLM hatası (deneme %d/%d): %s", attempt, MAX_RETRIES + 1, exc)

            # Son deneme değilse bekle
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

        logger.error("LLM tüm denemeler başarısız. Son hata: %s", last_error)
        return self._fallback_explanation(fusion)

    async def _call_api(self, prompt: str) -> str:
        """
        Gemini API'ye senkron çağrıyı async olarak çalıştırır.
        google-genai paketi sync olduğu için executor kullanılır.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
            ),
        )
        return response.text

    def _fallback_explanation(self, fusion: FusionInput) -> str:
        """
        Tüm denemeler başarısız olduğunda döndürülen fallback metin.
        """
        score_percent = round(fusion.final_score * 100)
        label_tr = {
            "fake": "sahte",
            "real": "gerçek",
            "uncertain": "belirsiz",
        }.get(fusion.final_label, "belirsiz")

        return (
            f"Sistem değerlendirmesine göre içerik %{score_percent} oranında "
            f"{label_tr} olarak sınıflandırıldı. "
            "Görsel, ses ve metin sinyalleri birlikte değerlendirilmiştir. "
            "Otomatik açıklama servisi şu an kullanılamıyor."
        )


# Uygulama genelinde tek örnek (singleton)
llm_service = LLMService()