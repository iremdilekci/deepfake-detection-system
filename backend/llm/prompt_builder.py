from __future__ import annotations

from dataclasses import dataclass


# ── Sistem Promptu ──────────────────────────────────────────────────────────
# LLM'e kim olduğunu ve nasıl davranması gerektiğini söyler.
# Her API çağrısında system mesajı olarak gönderilir.

SYSTEM_PROMPT = """Sen VeraDeep adlı bir deepfake tespit sisteminin açıklama motorusun.

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
"""


# ── Veri Sınıfları ───────────────────────────────────────────────────────────

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


# ── Prompt Builder ───────────────────────────────────────────────────────────

def build_user_prompt(
    modalities: list[ModalityInput],
    fusion: FusionInput,
) -> str:
    """
    OpenAI API'ye gönderilecek kullanıcı mesajını oluşturur.

    Parametreler:
    - modalities: Her modaliteye ait skor ve güven bilgisi
    - fusion: Late fusion sonucu (final skor, etiket, uyarılar)

    Döndürür:
    - str: Formatlanmış kullanıcı prompt metni
    """

    # Final skor yüzdeye çevir
    final_percent = round(fusion.final_score * 100)

    # Final etiket Türkçe'ye çevir
    label_tr = {
        "fake": "SAHTE",
        "real": "GERÇEK",
        "uncertain": "BELİRSİZ",
    }.get(fusion.final_label, "BELİRSİZ")

    # Modalite satırlarını oluştur
    modality_lines = []
    for m in modalities:
        if not m.available:
            modality_lines.append(
                f"- {m.label}: Analiz tamamlanamadı (devre dışı)"
            )
            continue

        score_percent = round(m.score * 100)
        confidence_percent = round(m.confidence * 100)
        verdict_tr = {
            "fake": "sahte",
            "real": "gerçek",
            "uncertain": "belirsiz",
        }.get(m.verdict, "belirsiz")

        modality_lines.append(
            f"- {m.label}: %{score_percent} deepfake olasılığı "
            f"(güven: %{confidence_percent}, karar: {verdict_tr}, "
            f"fusion ağırlığı: %{round(m.weight * 100)})"
        )

    modality_block = "\n".join(modality_lines)

    # Hata ve uyarı bloğu
    warning_block = ""
    if fusion.confidence_note:
        warning_block += f"\nUyarı: {fusion.confidence_note}"
    if fusion.errors:
        warning_block += f"\nHatalar: {'; '.join(fusion.errors)}"

    # Final prompt
    prompt = f"""Aşağıda bir videonun deepfake analiz sonuçları yer almaktadır.

=== ANALİZ SONUÇLARI ===

Final Karar: {label_tr}
Final Skor: %{final_percent} (deepfake olasılığı)

Modalite Detayları:
{modality_block}
{warning_block}

=== GÖREV ===
Bu analiz sonuçlarını kullanıcıya açıklayan, anlaşılır ve tarafsız bir Türkçe metin yaz.
Sistem kurallarına uy: maksimum 4 cümle, olasılık dili kullan, hangi modalite ne kadar katkı sağladığını belirt."""

    return prompt.strip()


def build_messages(
    modalities: list[ModalityInput],
    fusion: FusionInput,
) -> list[dict[str, str]]:
    """
    OpenAI API'nin beklediği messages formatını döndürür.

    Kullanım:
        messages = build_messages(modalities, fusion)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": build_user_prompt(modalities, fusion)},
    ]