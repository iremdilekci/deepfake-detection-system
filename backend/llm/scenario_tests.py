"""
VeraDeep LLM Senaryo Testleri
==============================
10 farklı senaryo ile prompt çıktı kalitesini değerlendirir.
Guardrail kontrolü her senaryo için ayrı ayrı çalıştırılır.

Çalıştırmak için:
    python -m llm.scenario_tests
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from llm.prompt_builder import (
    FusionInput,
    ModalityInput,
    LLMOutput,
    PROMPT_VARIANTS,
    build_user_prompt_variant,
    run_guardrails,
    apply_guardrails_or_fallback,
    _build_template_explanation,
)


# ══════════════════════════════════════════════════════════════════════════════
# TEST SENARYOLARI
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Scenario:
    id: str
    name: str
    modalities: list[ModalityInput]
    fusion: FusionInput
    expected_label: str        # Beklenen final etiket
    expected_keyword: str      # Açıklamada bulunması beklenen kelime
    variant: str = "A"


SCENARIOS: list[Scenario] = [

    # S01 — Klasik deepfake: tüm modaliteler yüksek fake sinyali
    Scenario(
        id="S01",
        name="Tüm modaliteler yüksek fake sinyali",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.87, 0.92, "fake", 0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.81, 0.88, "fake", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.74, 0.79, "fake", 0.20, True),
        ],
        fusion=FusionInput(0.83, "fake", None, []),
        expected_label="fake",
        expected_keyword="sahte",
    ),

    # S02 — Gerçek içerik: tüm modaliteler düşük skor
    Scenario(
        id="S02",
        name="Tüm modaliteler gerçek sinyali",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.12, 0.91, "real", 0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.18, 0.85, "real", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.21, 0.78, "real", 0.20, True),
        ],
        fusion=FusionInput(0.16, "real", None, []),
        expected_label="real",
        expected_keyword="gerçek",
    ),

    # S03 — Belirsiz: tüm modaliteler orta bölgede
    Scenario(
        id="S03",
        name="Belirsiz sonuç — tüm modaliteler orta bölge",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.52, 0.61, "uncertain", 0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.48, 0.58, "uncertain", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.55, 0.63, "uncertain", 0.20, True),
        ],
        fusion=FusionInput(0.51, "uncertain", None, []),
        expected_label="uncertain",
        expected_keyword="belirsiz",
    ),

    # S04 — Sessiz video: ses analizi yok
    Scenario(
        id="S04",
        name="Sessiz video — ses modalitesi devre dışı",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.79, 0.88, "fake", 0.714, True),
            ModalityInput("audio",  "Ses Analizi",   0.0,  0.0,  "uncertain", 0.0, False),
            ModalityInput("text",   "Metin Analizi", 0.61, 0.72, "uncertain", 0.286, True),
        ],
        fusion=FusionInput(0.739, "fake", "Ses modalitesi mevcut değil. Sonuç güvenilirliği düşük olabilir.", []),
        expected_label="fake",
        expected_keyword="ses",
    ),

    # S05 — Sadece görsel var, diğerleri başarısız
    Scenario(
        id="S05",
        name="Yalnızca görsel modalite mevcut",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.71, 0.84, "fake", 1.0, True),
            ModalityInput("audio",  "Ses Analizi",   0.0,  0.0,  "uncertain", 0.0, False),
            ModalityInput("text",   "Metin Analizi", 0.0,  0.0,  "uncertain", 0.0, False),
        ],
        fusion=FusionInput(0.71, "fake", "Yalnızca görsel modalite mevcut. Sonuç güvenilirliği düşük.", ["Ses analizi tamamlanamadı.", "Metin analizi tamamlanamadı."]),
        expected_label="fake",
        expected_keyword="görsel",
    ),

    # S06 — Çelişkili sinyaller: görsel fake, ses real
    Scenario(
        id="S06",
        name="Çelişkili sinyaller — görsel fake, ses real",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.78, 0.85, "fake",     0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.22, 0.79, "real",     0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.51, 0.65, "uncertain", 0.20, True),
        ],
        fusion=FusionInput(0.568, "uncertain", None, []),
        expected_label="uncertain",
        expected_keyword="belirsiz",
    ),

    # S07 — Düşük güven: tüm modeller az emin
    Scenario(
        id="S07",
        name="Düşük güven — modeller az emin",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.66, 0.28, "fake",     0.25, True),
            ModalityInput("audio",  "Ses Analizi",   0.71, 0.25, "fake",     0.15, True),
            ModalityInput("text",   "Metin Analizi", 0.58, 0.27, "uncertain", 0.10, True),
        ],
        fusion=FusionInput(0.667, "fake", "Modalite güven seviyeleri düşük. Sonuç güvenilirliği sınırlı.", []),
        expected_label="fake",
        expected_keyword="sahte",
    ),

    # S08 — Yüksek güvenle gerçek içerik
    Scenario(
        id="S08",
        name="Yüksek güven — kesin gerçek içerik",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.08, 0.95, "real", 0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.11, 0.93, "real", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.14, 0.91, "real", 0.20, True),
        ],
        fusion=FusionInput(0.10, "real", None, []),
        expected_label="real",
        expected_keyword="gerçek",
    ),

    # S09 — Sınır değer: fake eşiğinin hemen üstü
    Scenario(
        id="S09",
        name="Sınır değer — fake eşiği (0.65)",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.67, 0.72, "fake",     0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.63, 0.68, "uncertain", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.61, 0.65, "uncertain", 0.20, True),
        ],
        fusion=FusionInput(0.651, "fake", None, []),
        expected_label="fake",
        expected_keyword="sahte",
    ),

    # S10 — Hata durumu: LLM açıklaması guardrail'i geçemiyor
    Scenario(
        id="S10",
        name="Guardrail testi — mutlak ifade içeren çıktı",
        modalities=[
            ModalityInput("visual", "Görsel Analiz", 0.82, 0.91, "fake", 0.50, True),
            ModalityInput("audio",  "Ses Analizi",   0.74, 0.85, "fake", 0.30, True),
            ModalityInput("text",   "Metin Analizi", 0.61, 0.78, "uncertain", 0.20, True),
        ],
        fusion=FusionInput(0.76, "fake", None, []),
        expected_label="fake",
        expected_keyword="sahte",
        variant="A",
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# TEST ÇALIŞTIRICI
# ══════════════════════════════════════════════════════════════════════════════

def run_scenario_without_api(scenario: Scenario) -> dict:
    """
    API çağrısı olmadan senaryo testi çalıştırır.
    Prompt kalitesi ve guardrail kontrolü değerlendirilir.
    Şablon tabanlı fallback çıktı üretir ve guardrail'den geçirir.
    """
    # Prompt oluştur
    prompt = build_user_prompt_variant(scenario.modalities, scenario.fusion, scenario.variant)

    # Şablon tabanlı açıklama üret (API olmadan)
    template_explanation = _build_template_explanation(scenario.fusion, scenario.modalities)

    # Guardrail kontrolü
    passed, issues = run_guardrails(template_explanation)

    # Beklenen kelime kontrolü
    keyword_found = scenario.expected_keyword.lower() in template_explanation.lower()

    return {
        "id": scenario.id,
        "name": scenario.name,
        "variant": scenario.variant,
        "expected_label": scenario.expected_label,
        "actual_label": scenario.fusion.final_label,
        "label_match": scenario.expected_label == scenario.fusion.final_label,
        "explanation": template_explanation,
        "prompt_length": len(prompt),
        "guardrail_passed": passed,
        "guardrail_issues": issues,
        "keyword_found": keyword_found,
        "expected_keyword": scenario.expected_keyword,
    }


async def run_scenario_with_api(scenario: Scenario, api_key: str) -> dict:
    """
    Gerçek Gemini API çağrısı ile senaryo testi çalıştırır.
    """
    from google import genai
    from llm.prompt_builder import PROMPT_VARIANTS, build_user_prompt_variant, apply_guardrails_or_fallback

    client = genai.Client(api_key=api_key)
    system_prompt = PROMPT_VARIANTS.get(scenario.variant, PROMPT_VARIANTS["A"])
    user_prompt = build_user_prompt_variant(scenario.modalities, scenario.fusion, scenario.variant)
    full_prompt = system_prompt + "\n\n" + user_prompt

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=full_prompt,
        )
        raw_text = response.text
        output = apply_guardrails_or_fallback(raw_text, scenario.fusion, scenario.modalities)
        explanation = output.explanation
        guardrail_passed = output.passed_guardrails
        guardrail_issues = output.guardrail_issues
    except Exception as e:
        explanation = f"API HATASI: {e}"
        guardrail_passed = False
        guardrail_issues = [str(e)]

    keyword_found = scenario.expected_keyword.lower() in explanation.lower()

    return {
        "id": scenario.id,
        "name": scenario.name,
        "variant": scenario.variant,
        "expected_label": scenario.expected_label,
        "actual_label": scenario.fusion.final_label,
        "label_match": scenario.expected_label == scenario.fusion.final_label,
        "explanation": explanation,
        "guardrail_passed": guardrail_passed,
        "guardrail_issues": guardrail_issues,
        "keyword_found": keyword_found,
        "expected_keyword": scenario.expected_keyword,
    }


def print_results(results: list[dict], use_api: bool = False) -> None:
    """Test sonuçlarını formatlı olarak yazdırır."""
    print("\n" + "="*70)
    print("VeraDeep LLM Senaryo Test Sonuçları")
    print("="*70)

    passed_count = 0
    total = len(results)

    for r in results:
        label_ok = "✅" if r["label_match"] else "❌"
        guardrail_ok = "✅" if r["guardrail_passed"] else "⚠️"
        keyword_ok = "✅" if r["keyword_found"] else "❌"

        all_passed = r["label_match"] and r["guardrail_passed"] and r["keyword_found"]
        if all_passed:
            passed_count += 1

        status = "✅ GEÇTI" if all_passed else "❌ BAŞARISIZ"

        print(f"\n[{r['id']}] {r['name']} — {status}")
        print(f"  Etiket:     {label_ok} Beklenen: {r['expected_label']} | Gerçek: {r['actual_label']}")
        print(f"  Guardrail:  {guardrail_ok}")
        if r["guardrail_issues"]:
            for issue in r["guardrail_issues"]:
                print(f"    ⚠️  {issue}")
        print(f"  Anahtar:    {keyword_ok} '{r['expected_keyword']}' kelimesi bulundu mu?")
        print(f"  Açıklama:   {r['explanation'][:120]}...")

    print("\n" + "="*70)
    print(f"SONUÇ: {passed_count}/{total} senaryo başarılı")
    print("="*70 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    use_api = bool(api_key)

    if use_api:
        print("Gemini API ile test çalıştırılıyor...")
        results = []
        for scenario in SCENARIOS:
            result = await run_scenario_with_api(scenario, api_key)
            results.append(result)
            await asyncio.sleep(5)  # Rate limit için bekleme
    else:
        print("API key bulunamadı. Şablon tabanlı test çalıştırılıyor...")
        results = [run_scenario_without_api(s) for s in SCENARIOS]

    print_results(results, use_api)


if __name__ == "__main__":
    asyncio.run(main())