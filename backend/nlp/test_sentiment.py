"""
VeraDeep NLP Duygu Analizi -- Test Script
Calistir: py -m nlp.test_sentiment  (backend/ dizininden)
"""

import json
import sys
import time
import io

# Windows konsol encoding sorununu coz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def main():
    print("=" * 65)
    print("  VeraDeep - Turkce Duygu Analizi (Sentiment Analysis) Testi")
    print("=" * 65)

    # -- 1. Preprocessing Testi --
    print("\n[1/3] On isleme (preprocessing) testi...")
    from nlp.preprocessing import preprocess_text

    test_cases = [
        (
            "RT @deepfake_news Bu video kesinlikle sahte! https://t.co/abcd123 #deepfake #AI",
            "Bu video kesinlikle sahte! deepfake AI",
        ),
        (
            "@kullanici1 @kullanici2 harika bir calisma olmus http://example.com",
            "harika bir calisma olmus",
        ),
        (
            "Normal bir yorum, temizlenecek bir sey yok.",
            "Normal bir yorum, temizlenecek bir sey yok.",
        ),
        (
            "   ",
            "",
        ),
    ]

    all_passed = True
    for raw, expected in test_cases:
        result = preprocess_text(raw)
        status = "[OK]" if result == expected else "[FAIL]"
        if result != expected:
            all_passed = False
        print(f"  {status} Girdi:    {raw!r}")
        print(f"       Cikti:   {result!r}")
        if result != expected:
            print(f"       Beklenen: {expected!r}")
        print()

    if all_passed:
        print("  [OK] Tum on isleme testleri gecti!\n")
    else:
        print("  [!] Bazi on isleme testleri basarisiz.\n")

    # -- 2. Model Yukleme --
    print("[2/3] Model yukleniyor (ilk calistirmada indirilecek)...")
    t0 = time.time()

    from nlp.sentiment import SentimentAnalyzer
    analyzer = SentimentAnalyzer()

    t1 = time.time()
    print(f"  [OK] Model yuklendi: {t1 - t0:.1f}s ({analyzer.device})\n")

    # -- 3. Duygu Analizi Testi --
    print("[3/3] Duygu analizi cikarimlar...\n")

    sample_comments = [
        "Bu video kesinlikle sahte, yuz ifadesi cok garip ve dogal degil.",
        "Harika bir calisma, deepfake tespiti cok onemli bir konu!",
        "Video paylasild ama gercek mi sahte mi bilemedim.",
        "@elonmusk bu videoyu izleyin https://youtube.com/watch?v=fake123 #trending",
        "Yapay zeka ile uretilmis bu goruntuler insanlari kandiriyor, cok tehlikeli!",
        "Teknoloji harika ilerliyor, bu tur araclar toplum icin faydali.",
        "RT @haberler Sahte video skandali buyuyor! Detaylar linkte https://t.co/xyz",
    ]

    results = []
    for comment in sample_comments:
        result = analyzer.analyze(comment)
        results.append(result)

        label_marker = {
            "positive": "[+]",
            "negative": "[-]",
            "neutral":  "[~]",
        }.get(result.sentiment_label, "[?]")

        print(f"  {label_marker} [{result.sentiment_label.upper():>8}] (guven: {result.confidence_score:.2%})")
        print(f"     Orijinal:   {result.text}")
        print(f"     Temiz:      {result.cleaned_text}")
        print()

    # -- JSON Cikti Gosterimi --
    print("-" * 65)
    print("Ornek JSON ciktisi (FastAPI response formati):\n")

    json_output = {
        "results": [r.model_dump() for r in results[:3]],
        "total": len(results[:3]),
    }
    print(json.dumps(json_output, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 65}")
    print(f"  [OK] Test tamamlandi - {len(results)} yorum analiz edildi.")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
