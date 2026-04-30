"use client";

/**
 * ModalityChart — Deepfake analiz skorlarını Recharts ile görselleştirir.
 *
 * İki sekme:
 * 1. "Özet" — Görsel, ses ve metin modalitelerinin bar chart karşılaştırması
 * 2. "Zaman Serisi" — Backend'den gelen saniye bazlı skor değişimi (line chart)
 *
 * Renk kodlaması:
 * - Kırmızı  → fake   (skor >= 65)
 * - Sarı     → uncertain (35-65 arası)
 * - Yeşil    → real   (skor < 35)
 */

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartDataDto, ModalityScoreDto } from "@/lib/analysis-contract";

interface ModalityChartProps {
  modalities: ModalityScoreDto[];
  chartData: ChartDataDto | null;
}

// Renk paleti — her modalite için sabit renk
const MODALITY_COLORS: Record<string, string> = {
  visual: "#6366f1", // indigo
  audio:  "#f59e0b", // amber
  text:   "#10b981", // emerald
};

// Verdict'e göre bar rengi belirle
function verdictColor(verdict: string | null, score: number | null): string {
  const s = score ?? 0;
  if (s >= 0.65) return "#ef4444"; // red — fake
  if (s < 0.35)  return "#22c55e"; // green — real
  return "#f59e0b";                // amber — uncertain
}

export default function ModalityChart({ modalities, chartData }: ModalityChartProps) {
  // "bar" veya "line" sekme seçimi
  const [activeTab, setActiveTab] = useState<"bar" | "line">("bar");

  // Bar chart için veri formatı: Recharts'ın beklediği {name, score, confidence} dizisi
  const barData = modalities.map((m) => ({
    name: m.label,
    "Deepfake Skoru":  Math.round((m.score ?? 0) * 100),
    "Güven":           Math.round((m.confidence ?? 0) * 100),
    // Renk bilgisi ekstra — CustomBar'da kullanılacak
    color: verdictColor(m.verdict, m.score),
  }));

  // Line chart için veri formatı: her saniye bir obje
  const lineData = chartData
    ? chartData.labels.map((label, i) => {
        const point: Record<string, string | number> = { zaman: label };
        chartData.datasets.forEach((ds) => {
          point[ds.label] = ds.data[i] ?? 0;
        });
        return point;
      })
    : [];

  return (
    <div className="rounded-[28px] border border-slate-200 bg-white p-5">
      {/* Başlık */}
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">Modalite Analiz Grafiği</p>
          <p className="mt-1 text-sm text-slate-500">
            Görsel, ses ve metin kanallarının deepfake skor dağılımı.
          </p>
        </div>

        {/* Sekme düğmeleri */}
        <div className="flex gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1">
          <button
            onClick={() => setActiveTab("bar")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeTab === "bar"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Özet
          </button>
          <button
            onClick={() => setActiveTab("line")}
            disabled={!chartData}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
              activeTab === "line"
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Zaman Serisi
          </button>
        </div>
      </div>

      {/* Bar Chart — Modalite özet karşılaştırması */}
      {activeTab === "bar" && (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={barData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 12, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `%${v}`}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(value: number, name: string) => [`%${value}`, name]}
              contentStyle={{
                borderRadius: 12,
                border: "1px solid #e2e8f0",
                fontSize: 12,
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
            />
            {/* Deepfake Skoru çubuğu — verdict'e göre renk */}
            <Bar
              dataKey="Deepfake Skoru"
              radius={[6, 6, 0, 0]}
              fill="#6366f1"
            />
            {/* Güven çubuğu — her zaman gri */}
            <Bar
              dataKey="Güven"
              radius={[6, 6, 0, 0]}
              fill="#cbd5e1"
            />
          </BarChart>
        </ResponsiveContainer>
      )}

      {/* Line Chart — Zaman serisi (saniye bazlı sinyal değişimi) */}
      {activeTab === "line" && chartData && (
        <>
          <p className="mb-3 text-xs text-slate-400">
            Video boyunca her modaliteden elde edilen deepfake sinyali (%0–100).
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={lineData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="zaman"
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                // Çok fazla etiket varsa her 5'te bir göster
                interval={Math.max(0, Math.floor(lineData.length / 10))}
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v) => `%${v}`}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value: number, name: string) => [`%${value}`, name]}
                contentStyle={{
                  borderRadius: 12,
                  border: "1px solid #e2e8f0",
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 12 }} />
              {/* Her dataset için ayrı çizgi */}
              {chartData.datasets.map((ds) => (
                <Line
                  key={ds.label}
                  type="monotone"
                  dataKey={ds.label}
                  stroke={
                    ds.label.toLowerCase().includes("gorsel") || ds.label.toLowerCase().includes("görsel")
                      ? MODALITY_COLORS.visual
                      : ds.label.toLowerCase().includes("ses")
                      ? MODALITY_COLORS.audio
                      : MODALITY_COLORS.text
                  }
                  strokeWidth={2}
                  dot={false}
                  // Animasyonlu çizim
                  isAnimationActive={true}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </>
      )}
    </div>
  );
}
