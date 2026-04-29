from __future__ import annotations

import logging
from google import genai

from config import settings
from llm.prompt_builder import ModalityInput, FusionInput, build_user_prompt, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMService:
    """
    Google Gemini API ile iletişim kuran servis katmanı.

    Sorumlulukları:
    - Gemini istemcisini başlatmak
    - Prompt'u build_user_prompt() ile oluşturmak
    - API çağrısını yapmak
    - Hata durumunda fallback metin döndürmek
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
               Hata durumunda fallback metin döner, exception fırlatmaz.
        """
        if not self.client:
            logger.warning("GEMINI_API_KEY tanımlı değil. Fallback metin döndürülüyor.")
            return self._fallback_explanation(fusion)

        try:
            prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(modalities, fusion)
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
            )
            explanation = response.text
            if not explanation or not explanation.strip():
                return self._fallback_explanation(fusion)
            return explanation.strip()

        except Exception as exc:
            logger.error("Gemini API hatası: %s", exc)
            return self._fallback_explanation(fusion)

    def _fallback_explanation(self, fusion: FusionInput) -> str:
        """
        Gemini API kullanılamadığında döndürülen fallback metin.
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