"""
VeraDeep NLP Katmanı — Sosyal medya yorumlarının duygu analizi modülü.

SentimentAnalyzer burada import edilmiyor çünkü torch/transformers
her ortamda kurulu olmayabilir. İhtiyaç duyulan yerde doğrudan import et:
    from nlp.sentiment import SentimentAnalyzer, get_analyzer
"""

# Sadece torch gerektirmeyen modülleri burada yükle
from nlp.schemas import SentimentResult       # noqa: F401
from nlp.preprocessing import preprocess_text # noqa: F401
