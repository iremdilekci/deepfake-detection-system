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
                sentiment="neutral",
                polarity=0.5,
                confidence_score=0.0,
                fake_comment_score=0.0,
                explanations=["Metin boş veya anlamsız."],
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

        # Polarity hesaplama: P(positive) - P(negative)
        polarity = 0.0
        for idx, prob in enumerate(probabilities):
            lbl = self._resolve_label(self._id2label.get(idx, f"LABEL_{idx}"))
            if lbl == "positive":
                polarity += prob.item()
            elif lbl == "negative":
                polarity -= prob.item()
        
        # Normalizasyon: [-1, 1] aralığını [0, 1] aralığına çek (video/ses ile aynı format)
        polarity_val = round((polarity + 1.0) / 2.0, 4)
        
        # Fake comment skoru ve açıklamaları hesapla
        fake_score, explanations = self._calculate_fake_score(text, polarity_val)

        return SentimentResult(
            text=text,
            cleaned_text=cleaned,
            sentiment=label,
            polarity=polarity_val,
            confidence_score=round(confidence, 4),
            fake_comment_score=fake_score,
            explanations=explanations,
        )

    def _calculate_fake_score(self, text: str, polarity: float) -> tuple[float, list[str]]:
        """Metnin sahte, bot veya spam olma olasılığını sezgisel kurallarla hesaplar."""
        score = 0.0
        explanations = []
        
        # 1. Aşırı büyük harf kullanımı
        upper_chars = sum(1 for c in text if c.isupper())
        if len(text) > 0 and (upper_chars / len(text)) > 0.3:
            score += 0.3
            explanations.append("Aşırı büyük harf kullanımı tespit edildi.")
            
        # 2. Şüpheli anahtar kelimeler
        spam_keywords = ["tıkla", "link", "kazan", "bedava", "kampanya", "kesinlikle", "sahte", "gerçek değil", "harika ötesi", "şok"]
        lower_text = text.lower()
        found_spam = [kw for kw in spam_keywords if kw in lower_text]
        if found_spam:
            score += min(0.4, len(found_spam) * 0.2)
            explanations.append(f"Şüpheli kelimeler bulundu: {', '.join(found_spam)}")
            
        # 3. Aşırı noktalama işaretleri
        if text.count('!') > 2 or text.count('?') > 2:
            score += 0.2
            explanations.append("Aşırı noktalama işareti kullanımı (spam belirtisi olabilir).")
            
        # 4. Polarity uç noktalarda ise (Normalleştirilmiş 0-1 aralığı için)
        if polarity < 0.05 or polarity > 0.95:
            score += 0.1
            explanations.append("Duygu analizi uç noktada, manipülatif olabilir.")
            
        score = min(1.0, score)
        if score == 0.0:
            explanations.append("Metin doğal ve organik görünüyor.")
            
        return round(score, 3), explanations

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        """
        Birden fazla metin için toplu duygu analizi.
        Hata yönetimi ve gerçek batch çıkarımı (inference) ile akış hızı iyileştirilmiştir.
        """
        results = []
        valid_texts = []
        valid_indices = []
        
        # 1. Ön işleme ve hata yönetimi
        for i, text in enumerate(texts):
            try:
                cleaned = preprocess_text(text)
                if not cleaned:
                    results.append(SentimentResult(
                        text=text,
                        cleaned_text="",
                        sentiment="neutral",
                        polarity=0.5,
                        confidence_score=0.0,
                        fake_comment_score=0.0,
                        explanations=["Metin boş veya anlamsız."]
                    ))
                else:
                    valid_texts.append(cleaned)
                    valid_indices.append((i, text, cleaned))
                    results.append(None) # Yer tutucu
            except Exception as e:
                logger.error("Metin ön işleme hatası: %s", e)
                results.append(SentimentResult(
                    text=text,
                    cleaned_text="",
                    sentiment="neutral",
                    polarity=0.5,
                    confidence_score=0.0,
                    fake_comment_score=0.0,
                    explanations=[f"Ön işleme hatası: {str(e)}"]
                ))

        if not valid_texts:
            return results

        # 2. Toplu Tokenize (Batch Tokenization) ve Çıkarım - Akış Hızı İyileştirmesi
        try:
            inputs = self.tokenizer(
                valid_texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                
            for idx, (orig_i, orig_text, cleaned_text) in enumerate(valid_indices):
                probs = probabilities[idx]
                predicted_idx = torch.argmax(probs).item()
                confidence = probs[predicted_idx].item()

                raw_label = self._id2label.get(predicted_idx, f"LABEL_{predicted_idx}")
                label = self._resolve_label(raw_label)

                polarity = 0.0
                for label_idx, prob in enumerate(probs):
                    lbl = self._resolve_label(self._id2label.get(label_idx, f"LABEL_{label_idx}"))
                    if lbl == "positive":
                        polarity += prob.item()
                    elif lbl == "negative":
                        polarity -= prob.item()
                
                # Normalizasyon: [-1, 1] -> [0, 1]
                polarity_val = round((polarity + 1.0) / 2.0, 4)
                fake_score, explanations = self._calculate_fake_score(orig_text, polarity_val)

                results[orig_i] = SentimentResult(
                    text=orig_text,
                    cleaned_text=cleaned_text,
                    sentiment=label,
                    polarity=polarity_val,
                    confidence_score=round(confidence, 4),
                    fake_comment_score=fake_score,
                    explanations=explanations,
                )

        except Exception as e:
            logger.error("Toplu model çıkarım hatası: %s", e)
            for orig_i, orig_text, cleaned_text in valid_indices:
                results[orig_i] = SentimentResult(
                    text=orig_text,
                    cleaned_text=cleaned_text,
                    sentiment="neutral",
                    polarity=0.5,
                    confidence_score=0.0,
                    fake_comment_score=0.0,
                    explanations=["Model çıkarım aşamasında hata oluştu."]
                )

        return results


@lru_cache(maxsize=1)
def get_analyzer(model_name: str = MODEL_NAME) -> SentimentAnalyzer:
    """
    Singleton pattern — model bir kere yüklenir, sonra cache'den döner.
    FastAPI dependency olarak kullanılabilir.
    """
    return SentimentAnalyzer(model_name=model_name)
