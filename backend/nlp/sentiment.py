"""
Türkçe duygu analizi (sentiment analysis) modülü.
Hugging Face transformers + PyTorch kullanarak 'savasy/bert-base-turkish-sentiment-cased'
modelini yükler ve çıkarım (inference) yapar.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from nlp.preprocessing import preprocess_text
from nlp.schemas import SentimentResult

logger = logging.getLogger(__name__)

# Model adı — Türkçe sentiment için eğitilmiş BERT
MODEL_NAME = "savasy/bert-base-turkish-sentiment-cased"

# Model etiketlerini standart etiketlere dönüştür
_LABEL_MAP: dict[str, str] = {
    "positive": "positive",
    "negative": "negative",
    "neutral": "neutral",
    # Bazı modeller LABEL_0, LABEL_1 gibi çıktı veriyor
    "LABEL_0": "negative",
    "LABEL_1": "positive",
    "LABEL_2": "neutral",
}


class SentimentAnalyzer:
    """
    Türkçe duygu analizi sınıfı.

    Model ilk kullanımda indirilir ve belleğe yüklenir.
    Sonraki çağrılarda bellekten servis edilir.

    Kullanım:
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("Bu video gerçekten sahte!")
        print(result.sentiment_label)  # "negative"
        print(result.confidence_score) # 0.94
    """

    def __init__(self, model_name: str = MODEL_NAME, device: str | None = None):
        """
        Args:
            model_name: Hugging Face model adı veya lokal yol.
            device: "cpu", "cuda" veya None (otomatik seçim).
        """
        self.model_name = model_name

        # Cihaz seçimi
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info("Model yükleniyor: %s → %s", model_name, self.device)

        # Tokenizer ve model yükleme
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()  # Inference moduna al

        # Model etiketlerini al
        self._id2label: dict[int, str] = self.model.config.id2label or {}

        logger.info("Model başarıyla yüklendi. Etiketler: %s", self._id2label)

    def _resolve_label(self, raw_label: str) -> str:
        """Ham model etiketini standart etikete dönüştürür."""
        normalized = raw_label.lower().strip()
        return _LABEL_MAP.get(normalized, _LABEL_MAP.get(raw_label, normalized))

    @torch.no_grad()
    def analyze(self, text: str) -> SentimentResult:
        """
        Tek bir metin için duygu analizi yapar.

        Args:
            text: Analiz edilecek sosyal medya metni.

        Returns:
            SentimentResult: text, cleaned_text, sentiment_label, confidence_score
        """
        # Ön işleme
        cleaned = preprocess_text(text)

        if not cleaned:
            return SentimentResult(
                text=text,
                cleaned_text="",
                sentiment_label="neutral",
                confidence_score=0.0,
            )

        # Tokenize
        inputs = self.tokenizer(
            cleaned,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Forward pass
        outputs = self.model(**inputs)
        logits = outputs.logits

        # Softmax → olasılıklar
        probabilities = torch.softmax(logits, dim=-1).squeeze()

        # En yüksek olasılıklı sınıf
        predicted_idx = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_idx].item()

        # Etiket çözümleme
        raw_label = self._id2label.get(predicted_idx, f"LABEL_{predicted_idx}")
        label = self._resolve_label(raw_label)

        return SentimentResult(
            text=text,
            cleaned_text=cleaned,
            sentiment_label=label,
            confidence_score=round(confidence, 4),
        )

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        """
        Birden fazla metin için toplu duygu analizi.

        Args:
            texts: Metin listesi.

        Returns:
            SentimentResult listesi.
        """
        return [self.analyze(t) for t in texts]


@lru_cache(maxsize=1)
def get_analyzer(model_name: str = MODEL_NAME) -> SentimentAnalyzer:
    """
    Singleton pattern — model bir kere yüklenir, sonra cache'den döner.
    FastAPI dependency olarak kullanılabilir.
    """
    return SentimentAnalyzer(model_name=model_name)
