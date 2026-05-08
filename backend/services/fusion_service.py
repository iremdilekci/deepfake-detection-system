# backend/services/fusion_service.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

# Varsayılan ağırlıklar
DEFAULT_WEIGHTS: dict[str, float] = {
    "visual": 0.50,
    "audio":  0.30,
    "text":   0.20,
}

# Final etiket eşikleri
FAKE_THRESHOLD      = 0.65
REAL_THRESHOLD      = 0.35
MIN_CONFIDENCE      = 0.30  # Bu değerin altındaki modalite yarı ağırlıkla katılır

# Fallback mesajları
FALLBACK_MESSAGES: dict[str, str] = {
    "visual": "Görsel analiz tamamlanamadı. Video formatı desteklenmiyor olabilir.",
    "audio":  "Ses analizi tamamlanamadı. Ses kanalı okunamıyor olabilir.",
    "text":   "Metin analizi tamamlanamadı. Yorum verisi bulunamadı.",
    "partial": "Analiz kısmi tamamlandı. Sonuç güvenilirliği düşük olabilir.",
    "all_failed": "Hiçbir modalite analizi tamamlanamadı. Lütfen videoyu kontrol edin.",
}


@dataclass
class ModalityResult:
    key: Literal["visual", "audio", "text"]
    score: float | None          # 0–1 arası, başarısızsa None
    confidence: float | None     # 0–1 arası, başarısızsa None
    available: bool              # Analiz başarıyla tamamlandı mı?
    skipped: bool = False        # Sessiz video gibi beklenen atlama durumu mu?


@dataclass
class FusionResult:
    final_score: float | None
    final_label: Literal["fake", "real", "uncertain"] | None
    weights: dict[str, float]    # Her modaliteye atanan nihai ağırlık
    errors: list[str]
    confidence_note: str | None


def compute_final_label(score: float) -> Literal["fake", "real", "uncertain"]:
    if score >= FAKE_THRESHOLD:
        return "fake"
    elif score < REAL_THRESHOLD:
        return "real"
    return "uncertain"


def run_fusion(modalities: list[ModalityResult]) -> FusionResult:
    """
    Late fusion algoritması.
    Mevcut modalitelerin ağırlıklı ortalamasını alır.
    Eksik modaliteleri fallback kurallarına göre yönetir.
    """
    errors: list[str] = []
    confidence_note: str | None = None

    # Adım 1: Başarısız modaliteleri tespit et ve hata mesajı ekle
    for modality in modalities:
        if not modality.available and not modality.skipped:
            errors.append(FALLBACK_MESSAGES[modality.key])

    # Adım 2: Aktif modalitelere ağırlık ata
    active_weights: dict[str, float] = {}
    for modality in modalities:
        if not modality.available:
            active_weights[modality.key] = 0.0
            continue

        weight = DEFAULT_WEIGHTS[modality.key]

        # Kural 4: Düşük güven → ağırlığı yarıya indir
        if modality.confidence is not None and modality.confidence < MIN_CONFIDENCE:
            weight *= 0.5

        active_weights[modality.key] = weight

    # Adım 3: Toplam ağırlık sıfırsa tüm analizler başarısız
    total_weight = sum(active_weights.values())
    if total_weight == 0.0:
        errors.append(FALLBACK_MESSAGES["all_failed"])
        return FusionResult(
            final_score=None,
            final_label=None,
            weights=active_weights,
            errors=errors,
            confidence_note=None,
        )

    # Adım 4: Ağırlıkları normalize et
    normalized_weights = {k: v / total_weight for k, v in active_weights.items()}

    # Adım 5: Ağırlıklı ortalama hesapla
    final_score = 0.0
    active_count = 0
    for modality in modalities:
        if modality.available and modality.score is not None:
            final_score += modality.score * normalized_weights[modality.key]
            active_count += 1

    # Adım 6: Kısmi analiz uyarısı
    total_modalities = len(modalities)
    if active_count < total_modalities:
        if active_count == 1:
            active_key = next(m.key for m in modalities if m.available)
            confidence_note = (
                f"Yalnızca {active_key} modalitesi mevcut. "
                "Sonuç güvenilirliği düşük."
            )
        else:
            errors.insert(0, FALLBACK_MESSAGES["partial"])

    return FusionResult(
        final_score=round(final_score, 4),
        final_label=compute_final_label(final_score),
        weights=normalized_weights,
        errors=errors,
        confidence_note=confidence_note,
    )