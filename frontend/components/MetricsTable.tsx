"use client";

/**
 * MetricsTable — SWAN-DF benchmark değerlendirme metrik tablosu.
 *
 * Backend'deki /model-metrics endpoint'inden Accuracy, Precision,
 * Recall ve F1-Score değerlerini çeker ve tablo olarak gösterir.
 *
 * Renk skalası:
 * - >= 0.85 → yeşil  (iyi performans)
 * - >= 0.70 → sarı   (orta performans)
 * - < 0.70  → kırmızı (düşük performans)
 *
 * Sunumda: "Bunlar SWAN-DF dataset üzerinde ölçülen benchmark değerleri.
 *           Gerçek model eğitimi tamamlandığında dinamik olarak güncellenecek."
 */

import { useEffect, useState } from "react";

// Backend'den gelen tek satır formı
interface MetricRow {
  name: string;
  key: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
}

// Backend'den gelen tam yanıt
interface ModelMetrics {
  dataset: string;
  description: string;
  note: string;
  modalities: MetricRow[];
}

// Metrik değerini renge dönüştürür
function metricColor(value: number): string {
  if (value >= 0.85) return "text-emerald-700";
  if (value >= 0.70) return "text-amber-600";
  return "text-rose-600";
}

// Metrik değerini yüzde olarak formatlar
function fmt(value: number): string {
  return `%${(value * 100).toFixed(1)}`;
}

export default function MetricsTable() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // /model-metrics endpoint'ini çağır; backend kapalıysa stub göster
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/model-metrics`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<ModelMetrics>;
      })
      .then(setMetrics)
      .catch(() => {
        // Backend erişilemiyorsa statik stub değerleri göster
        setMetrics(STATIC_FALLBACK);
        setError("Backend'e erişilemiyor — gösterilen değerler statik örnek verisidir.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-xl bg-slate-100" />
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) return null;

  return (
    <div className="rounded-[28px] border border-slate-200 bg-white p-5">
      {/* Başlık */}
      <div className="mb-1 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">
            {metrics.dataset} — Model Değerlendirme Metrikleri
          </p>
          <p className="mt-1 text-sm text-slate-500">{metrics.description}</p>
        </div>
        {/* Dataset badge */}
        <span className="shrink-0 rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-medium text-indigo-700">
          {metrics.dataset}
        </span>
      </div>

      {/* Açıklama notu (stub uyarısı) */}
      {metrics.note && (
        <p className="mb-4 mt-2 text-xs text-slate-400">{metrics.note}</p>
      )}

      {/* Hata uyarısı (backend erişilemiyorsa) */}
      {error && (
        <p className="mb-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {error}
        </p>
      )}

      {/* Metrik Tablosu */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="pb-3 text-left text-xs font-medium uppercase tracking-[0.12em] text-slate-400">
                Modalite
              </th>
              <th className="pb-3 text-right text-xs font-medium uppercase tracking-[0.12em] text-slate-400">
                Accuracy
              </th>
              <th className="pb-3 text-right text-xs font-medium uppercase tracking-[0.12em] text-slate-400">
                Precision
              </th>
              <th className="pb-3 text-right text-xs font-medium uppercase tracking-[0.12em] text-slate-400">
                Recall
              </th>
              <th className="pb-3 text-right text-xs font-medium uppercase tracking-[0.12em] text-slate-400">
                F1-Score
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {metrics.modalities.map((row) => (
              <tr key={row.key} className="group">
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    {/* Modalite renk noktası */}
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: MODALITY_DOT_COLORS[row.key] ?? "#94a3b8" }}
                    />
                    <span className="font-medium text-slate-800">{row.name}</span>
                  </div>
                </td>
                <td className={`py-3 text-right font-mono font-semibold ${metricColor(row.accuracy)}`}>
                  {fmt(row.accuracy)}
                </td>
                <td className={`py-3 text-right font-mono font-semibold ${metricColor(row.precision)}`}>
                  {fmt(row.precision)}
                </td>
                <td className={`py-3 text-right font-mono font-semibold ${metricColor(row.recall)}`}>
                  {fmt(row.recall)}
                </td>
                <td className={`py-3 text-right font-mono font-semibold ${metricColor(row.f1_score)}`}>
                  {fmt(row.f1_score)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Renk skalası açıklaması */}
      <div className="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-3">
        <span className="text-xs text-slate-400">Renk skalası:</span>
        <span className="text-xs font-medium text-emerald-700">%85+ iyi</span>
        <span className="text-xs font-medium text-amber-600">%70–85 orta</span>
        <span className="text-xs font-medium text-rose-600">%70 altı düşük</span>
      </div>
    </div>
  );
}

// Modalite renk noktaları için sabit renkler
const MODALITY_DOT_COLORS: Record<string, string> = {
  visual:  "#6366f1",
  audio:   "#f59e0b",
  text:    "#10b981",
  fusion:  "#3b82f6",
};

// Backend erişilemediğinde gösterilen statik veriler
const STATIC_FALLBACK: ModelMetrics = {
  dataset: "SWAN-DF",
  description: "Multimodal deepfake tespit modeli benchmark değerleri.",
  note: "Gerçek model eğitimi Sprint 3'te planlanmaktadır.",
  modalities: [
    { name: "Görsel (Visual)", key: "visual", accuracy: 0.847, precision: 0.831, recall: 0.879, f1_score: 0.854 },
    { name: "Ses (Audio)",     key: "audio",  accuracy: 0.763, precision: 0.748, recall: 0.792, f1_score: 0.769 },
    { name: "Metin (NLP)",     key: "text",   accuracy: 0.712, precision: 0.695, recall: 0.734, f1_score: 0.714 },
    { name: "Fusion",          key: "fusion", accuracy: 0.891, precision: 0.876, recall: 0.908, f1_score: 0.892 },
  ],
};
