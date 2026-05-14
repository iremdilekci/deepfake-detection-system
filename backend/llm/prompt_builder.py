from __future__ import annotations

import json
import re
from dataclasses import dataclass


# ══════════════════════════════════════════════════════════════════════════════
# SİSTEM PROMPTLARI — A/B VARYANTLARI
# ══════════════════════════════════════════════════════════════════════════════

# PROMPT A — Standart açıklama (mevcut, üretimde kullanılan)
# Odak: Modalite katkıları + olasılık dili
SYSTEM_PROMPT_A = """Sen VeraDeep adlı bir deepfake tespit sisteminin açıklama motorusun.

Görevin:
- Sana verilen görsel, ses ve metin analiz skorlarını yorumlamak
- Kullanıcıya açık, anlaşılır ve tarafsız bir Türkçe açıklama üretmek
- Teknik terimleri sade bir dille açıklamak
- Kesin yargıdan kaçınmak, olasılık dili kullanmak

Kurallar:
- Yanıtın her zaman Türkçe olacak
- Maksimum 4 cümle yaz
- "Bu kesinlikle sahtedir" gibi mutlak ifadeler kullanma
- "Bu kesinlikle gerçektir" gibi mutlak ifadeler kullanma
- Her zaman "analiz sonuçlarına göre" veya "sistem değerlendirmesine göre" gibi ifadelerle başla
- Hangi modalite (görsel/ses/metin) ne kadar katkı sağladığını belirt
- Güven düşükse bunu kullanıcıya açıkça belirt
- Yanıtın yalnızca açıklama metni olacak, başka hiçbir şey ekleme
"""

# PROMPT B — Risk odaklı açıklama
# Odak: Kullanıcıya risk değerlendirmesi + ne yapmalı önerisi
SYSTEM_PROMPT_B = """Sen VeraDeep adlı bir deepfake tespit sisteminin risk değerlendirme motorusun.

Görevin:
- Analiz sonuçlarını risk perspektifinden yorumlamak
- Kullanıcıya içeriğin güvenilirliği hakkında net bir değerlendirme sunmak
- Olası riskleri ve içeriğe nasıl yaklaşılması gerektiğini belirtmek

Kurallar:
- Yanıtın her zaman Türkçe olacak
- Maksimum 4 cümle yaz
- Mutlak ifadeler kullanma, olasılık dili kullan
- "Bu analiz sonuçlarına göre" ifadesiyle başla
- Risk seviyesini belirt: düşük / orta / yüksek
- İçeriğin paylaşılması veya kullanılması konusunda dikkatli bir öneri ekle
- Yanıtın yalnızca açıklama metni olacak, başka hiçbir şey ekleme
"""

# PROMPT C — Teknik özet
# Odak: Akademik/teknik kullanıcılar için sayısal özet
SYSTEM_PROMPT_C = """Sen VeraDeep adlı bir deepfake tespit sisteminin teknik özet motorusun.

Görevin:
- Analiz sonuçlarını teknik ve sayısal olarak özetlemek
- Her modalite skorunu ve fusion sonucunu kısa açıklamalarla sunmak

Kurallar:
- Yanıtın her zaman Türkçe olacak
- Maksimum 4 cümle yaz
- Her modalite için skor ve güven değerini belirt
- Final fusion skoru ve etiketi açık şekilde ifade et
- Mutlak ifadeler kullanma
- Yanıtın yalnızca açıklama metni olacak, başka hiçbir şey ekleme
"""

# Üretimde kullanılan varsayılan prompt
SYSTEM_PROMPT = SYSTEM_PROMPT_A

# A/B test için tüm varyantlar
PROMPT_VARIANTS = {
    "A": SYSTEM_PROMPT_A,
    "B": SYSTEM_PROMPT_B,
    "C": SYSTEM_PROMPT_C,
}


# ══════════════════════════════════════════════════════════════════════════════
# VERİ SINIFLARI
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ModalityInput:
    """LLM'e gönderilecek tek modalite bilgisi."""
    key: str            # "visual" | "audio" | "text"
    label: str          # "Görsel Analiz" | "Ses Analizi" | "Metin Analizi"
    score: float        # 0.0 – 1.0
    confidence: float   # 0.0 – 1.0
    verdict: str        # "fake" | "real" | "uncertain"
    weight: float       # Fusion'daki ağırlık (normalize edilmiş)
    available: bool     # Analiz tamamlandı mı?


@dataclass
class FusionInput:
    """LLM'e gönderilecek fusion sonucu."""
    final_score: float          # 0.0 – 1.0
    final_label: str            # "fake" | "real" | "uncertain"
    confidence_note: str | None # Eksik modalite uyarısı
    errors: list[str]           # Analiz sırasında oluşan hatalar


@dataclass
class LLMOutput:
    """
    LLM'den dönen ve doğrulanan çıktı.

    Alanlar:
    - explanation: Kullanıcıya gösterilecek açıklama metni
    - variant: Hangi prompt varyantı kullanıldı (A/B/C)
    - passed_guardrails: Guardrail kontrolünden geçti mi?
    - guardrail_issues: Tespit edilen sorunların listesi
    """
    explanation: str
    variant: str
    passed_guardrails: bool
    guardrail_issues: list[str]


# ══════════════════════════════════════════════════════════════════════════════
# MODALİTE BAZLI AÇIKLAMA ŞABLONLARI
# ══════════════════════════════════════════════════════════════════════════════

MODALITY_TEMPLATES = {
    "visual": {
        "fake":      "Görsel analiz, video karelerinde deepfake belirtileri tespit etti (%{score} olasılık).",
        "real":      "Görsel analiz, video karelerinde deepfake belirtisi tespit etmedi (%{score} olasılık).",
        "uncertain": "Görsel analiz sonucu belirsiz; yüz bölgesinde kısmi tutarsızlıklar gözlemlendi (%{score} olasılık).",
        "unavailable": "Görsel analiz tamamlanamadı; video formatı işlenemedi.",
    },
    "audio": {
        "fake":      "Ses analizi, konuşma akışında ve dudak hareketlerinde uyumsuzluklar tespit etti (%{score} olasılık).",
        "real":      "Ses analizi, konuşma ve görüntü senkronizasyonunun tutarlı olduğunu gösterdi (%{score} olasılık).",
        "uncertain": "Ses analizi sonucu belirsiz; kısmi lip-sync uyumsuzluğu gözlemlendi (%{score} olasılık).",
        "unavailable": "Ses analizi tamamlanamadı; video ses kanalı içermiyor veya okunamadı.",
    },
    "text": {
        "fake":      "Metin analizi, içerikle ilişkili yorumlarda sahte içerik örüntüleri tespit etti (%{score} olasılık).",
        "real":      "Metin analizi, içerikle ilişkili yorumlarda anormal bir örüntü tespit etmedi (%{score} olasılık).",
        "uncertain": "Metin analizi sonucu belirsiz; yorum verileri sınırlı (%{score} olasılık).",
        "unavailable": "Metin analizi tamamlanamadı; yorum verisi bulunamadı.",
    },
}


def get_modality_explanation(key: str, verdict: str, score: float) -> str:
    """
    Bir modalite için şablon tabanlı açıklama üretir.
    LLM yetersiz kaldığında veya fallback gerektiğinde kullanılır.
    """
    templates = MODALITY_TEMPLATES.get(key, {})
    template = templates.get(verdict, templates.get("uncertain", "Analiz sonucu mevcut değil."))
    return template.replace("%{score}", str(round(score * 100)))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL KURALLARI
# ══════════════════════════════════════════════════════════════════════════════

# Mutlak ifadeler — LLM çıktısında bulunmamalı
FORBIDDEN_ABSOLUTE_PHRASES = [
    "kesinlikle sahtedir",
    "kesinlikle gerçektir",
    "100% sahte",
    "100% gerçek",
    "şüphe yok",
    "tartışmasız",
    "kanıtlanmıştır",
    "ispatlanmıştır",
    "garantidir",
    "mutlaka sahte",
    "mutlaka gerçek",
]

# Zorunlu başlangıç ifadeleri — LLM çıktısı bunlardan biriyle başlamalı
REQUIRED_OPENING_PHRASES = [
    "analiz sonuçlarına göre",
    "sistem değerlendirmesine göre",
    "bu analiz sonuçlarına göre",
    "yapılan analize göre",
    "değerlendirme sonuçlarına göre",
]

# Minimum ve maksimum cümle sayısı
MIN_SENTENCES = 1
MAX_SENTENCES = 5

# Minimum karakter sayısı
MIN_CHARS = 50


def run_guardrails(text: str) -> tuple[bool, list[str]]:
    """
    LLM çıktısını guardrail kurallarına göre denetler.

    Döndürür:
    - bool: Tüm kuralları geçti mi?
    - list[str]: Tespit edilen sorunların listesi
    """
    issues: list[str] = []
    text_lower = text.lower().strip()

    # Kural 1: Boş veya çok kısa çıktı
    if len(text.strip()) < MIN_CHARS:
        issues.append(f"Çıktı çok kısa (min {MIN_CHARS} karakter).")

    # Kural 2: Mutlak ifadeler yasak
    for phrase in FORBIDDEN_ABSOLUTE_PHRASES:
        if phrase in text_lower:
            issues.append(f"Mutlak ifade tespit edildi: '{phrase}'")

    # Kural 3: Zorunlu başlangıç ifadesi
    has_opening = any(text_lower.startswith(p) for p in REQUIRED_OPENING_PHRASES)
    if not has_opening:
        issues.append("Çıktı zorunlu başlangıç ifadesiyle başlamıyor.")

    # Kural 4: Cümle sayısı kontrolü
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if len(sentences) > MAX_SENTENCES:
        issues.append(f"Çok fazla cümle ({len(sentences)} > {MAX_SENTENCES}).")

    # Kural 5: Türkçe karakter kontrolü (en az 3 Türkçe kelime)
    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    turkish_word_count = sum(1 for word in text.split() if any(c in turkish_chars for c in word))
    if turkish_word_count < 2:
        issues.append("Çıktı Türkçe görünmüyor.")

    # Kural 6: JSON veya kod bloğu içermemeli
    if "```" in text or "{" in text or "}" in text:
        issues.append("Çıktı kod bloğu veya JSON içeriyor.")

    passed = len(issues) == 0
    return passed, issues


def apply_guardrails_or_fallback(
    text: str,
    fusion: FusionInput,
    modalities: list[ModalityInput],
) -> LLMOutput:
    """
    Guardrail kontrolü yapar.
    Başarısız olursa şablon tabanlı fallback açıklama üretir.
    """
    passed, issues = run_guardrails(text)

    if passed:
        return LLMOutput(
            explanation=text,
            variant="A",
            passed_guardrails=True,
            guardrail_issues=[],
        )

    # Guardrail başarısız → şablon tabanlı fallback
    fallback = _build_template_explanation(fusion, modalities)
    return LLMOutput(
        explanation=fallback,
        variant="fallback",
        passed_guardrails=False,
        guardrail_issues=issues,
    )


def _build_template_explanation(
    fusion: FusionInput,
    modalities: list[ModalityInput],
) -> str:
    """Şablon tabanlı güvenli fallback açıklama."""
    score_percent = round(fusion.final_score * 100)
    label_tr = {
        "fake": "sahte olma ihtimali yüksek",
        "real": "gerçek olma ihtimali yüksek",
        "uncertain": "belirsiz",
    }.get(fusion.final_label, "belirsiz")

    parts = [
        f"Analiz sonuçlarına göre bu içerik %{score_percent} oranında {label_tr} olarak değerlendirilmiştir."
    ]

    for m in modalities:
        if m.available:
            parts.append(get_modality_explanation(m.key, m.verdict, m.score))

    if fusion.confidence_note:
        parts.append(f"Not: {fusion.confidence_note}")

    return " ".join(parts[:4])  # Maksimum 4 cümle


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_user_prompt(
    modalities: list[ModalityInput],
    fusion: FusionInput,
) -> str:
    """
    LLM'e gönderilecek kullanıcı mesajını oluşturur.
    """
    final_percent = round(fusion.final_score * 100)
    label_tr = {
        "fake": "SAHTE",
        "real": "GERÇEK",
        "uncertain": "BELİRSİZ",
    }.get(fusion.final_label, "BELİRSİZ")

    modality_lines = []
    for m in modalities:
        if not m.available:
            modality_lines.append(f"- {m.label}: Analiz tamamlanamadı (devre dışı)")
            continue

        score_percent = round(m.score * 100)
        confidence_percent = round(m.confidence * 100)
        verdict_tr = {"fake": "sahte", "real": "gerçek", "uncertain": "belirsiz"}.get(m.verdict, "belirsiz")
        modality_lines.append(
            f"- {m.label}: %{score_percent} deepfake olasılığı "
            f"(güven: %{confidence_percent}, karar: {verdict_tr}, "
            f"fusion ağırlığı: %{round(m.weight * 100)})"
        )

    modality_block = "\n".join(modality_lines)

    warning_block = ""
    if fusion.confidence_note:
        warning_block += f"\nUyarı: {fusion.confidence_note}"
    if fusion.errors:
        warning_block += f"\nHatalar: {'; '.join(fusion.errors)}"

    prompt = f"""Aşağıda bir videonun deepfake analiz sonuçları yer almaktadır.

=== ANALİZ SONUÇLARI ===

Final Karar: {label_tr}
Final Skor: %{final_percent} (deepfake olasılığı)

Modalite Detayları:
{modality_block}
{warning_block}

=== GÖREV ===
Bu analiz sonuçlarını kullanıcıya açıklayan, anlaşılır ve tarafsız bir Türkçe metin yaz.
Sistem kurallarına uy: maksimum 4 cümle, olasılık dili kullan, hangi modalite ne kadar katkı sağladığını belirt.
Yanıtın yalnızca açıklama metni olsun, başka hiçbir şey ekleme."""

    return prompt.strip()


def build_user_prompt_variant(
    modalities: list[ModalityInput],
    fusion: FusionInput,
    variant: str = "A",
) -> str:
    """
    Belirli bir prompt varyantı için kullanıcı mesajı oluşturur.
    variant: "A" | "B" | "C"
    """
    base_prompt = build_user_prompt(modalities, fusion)

    if variant == "B":
        # Risk odaklı varyant için ek yönerge
        base_prompt += "\n\nAyrıca içeriğin risk seviyesini (düşük/orta/yüksek) belirt ve kullanıcıya bir öneri ekle."

    elif variant == "C":
        # Teknik varyant için ek yönerge
        base_prompt += "\n\nHer modalite skorunu ve güven değerini sayısal olarak belirt."

    return base_prompt


def build_messages(
    modalities: list[ModalityInput],
    fusion: FusionInput,
    variant: str = "A",
) -> list[dict[str, str]]:
    """
    API'nin beklediği messages formatını döndürür.
    variant: "A" | "B" | "C"
    """
    system_prompt = PROMPT_VARIANTS.get(variant, SYSTEM_PROMPT_A)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": build_user_prompt_variant(modalities, fusion, variant)},
    ]