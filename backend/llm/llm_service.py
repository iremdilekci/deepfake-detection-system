"""
LLM Servisi — Google Gemini API ile Türkçe deepfake açıklaması üretir.

Özellikler:
- GEMINI_API_KEY .env'de tanımlı değilse sessizce fallback metin döndürür.
- Her çağrı maksimum 30 saniye bekler (timeout).
- Geçici hatalarda 2 kez yeniden dener.
- Dakika başına 12 istek limiti (RateLimiter ile).
"""

from __future__ import annotations

import asyncio
import logging

from config import settings
from llm.prompt_builder import FusionInput, ModalityInput, build_user_prompt, SYSTEM_PROMPT
from llm.rate_limiter import gemini_limiter

logger = logging.getLogger(__name__)

# Tek API çağrısı için zaman aşımı süresi (saniye)
TIMEOUT_SECONDS = 30
# Geçici hatalarda maksimum yeniden deneme sayısı
MAX_RETRIES = 2
# Yeniden denemeler arası bekleme süresi (saniye, her denemede artar)
RETRY_DELAY_SECONDS = 2.0


class LLMService:
    """
    Google Gemini API ile iletişim kuran servis sınıfı.

    Analiz sonuçlarını (modalite skorları + fusion) alır,
    Gemini'ye gönderir ve Türkçe açıklama metni döndürür.

    API key yoksa veya çağrı başarısız olursa exception fırlatmaz,
    bunun yerine basit bir fallback metin döndürür.
    """

    # Kullanılan Gemini modeli — ücretsiz tier'da hızlı ve yeterince yetenekli
    MODEL = "gemini-2.0-flash-lite"

    def __init__(self) -> None:
        # API key varsa istemciyi başlat, yoksa None bırak
        if settings.gemini_api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("Gemini LLM servisi başlatıldı. Model: %s", self.MODEL)
            except ImportError:
                logger.warning("google-genai paketi yüklü değil. LLM devre dışı.")
                self.client = None
        else:
            logger.warning("GEMINI_API_KEY tanımlı değil. LLM fallback modunda çalışacak.")
            self.client = None

    async def generate_explanation(
        self,
        modalities: list[ModalityInput],
        fusion: FusionInput,
    ) -> str:
        """
        Modalite skorları ve fusion sonucuna göre Türkçe açıklama üretir.

        Args:
            modalities: Görsel, ses, metin skorları ve güven değerleri
            fusion:     Late fusion sonucu (final skor, etiket, uyarılar)

        Returns:
            Türkçe açıklama metni.
            API çağrısı başarısız olursa fallback metin döner.
        """
        if not self.client:
            return self._fallback_explanation(fusion)

        # Sistem promptu + kullanıcı mesajını birleştir
        full_prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(modalities, fusion)
        last_error: Exception | None = None

        # Toplam deneme sayısı: MAX_RETRIES + 1 (ilk deneme dahil)
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                await gemini_limiter.acquire()

                # Timeout ile sarılmış async API çağrısı
                explanation = await asyncio.wait_for(
                    self._call_api(full_prompt),
                    timeout=TIMEOUT_SECONDS,
                )

                if not explanation or not explanation.strip():
                    return self._fallback_explanation(fusion)

                logger.info("LLM açıklaması üretildi (deneme %d).", attempt)
                return explanation.strip()

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(f"API zaman aşımı ({TIMEOUT_SECONDS}s)")
                logger.warning("LLM zaman aşımı (deneme %d/%d).", attempt, MAX_RETRIES + 1)

            except Exception as exc:
                last_error = exc
                logger.warning("LLM hatası (deneme %d/%d): %s", attempt, MAX_RETRIES + 1, exc)

            # Son deneme değilse bir süre bekle
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

        logger.error("LLM tüm denemeler başarısız. Son hata: %s", last_error)
        return self._fallback_explanation(fusion)

    async def _call_api(self, prompt: str) -> str:
        """
        Gemini API'ye senkron çağrıyı thread pool üzerinden async olarak çalıştırır.
        google-genai paketi blocking/sync olduğu için executor gereklidir.
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
        API kullanılamadığında gösterilen yedek açıklama metni.
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


# Uygulama genelinde tek örnek — her modül bu nesneyi import eder
llm_service = LLMService()
