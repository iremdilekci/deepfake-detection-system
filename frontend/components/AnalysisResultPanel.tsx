"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend as ChartJSLegend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

import { AnalysisResultViewModel, AnalysisStatus, UploadSummary } from "@/lib/analysis-contract";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  ChartJSLegend,
  Filler
);

interface AnalysisResultPanelProps {
  result: AnalysisResultViewModel | null;
  status: AnalysisStatus | null;
  uploadSummary: UploadSummary | null;
  selectedFile: File | null;
  isBusy: boolean;
  onRetry: () => void;
  onReset: () => void;
}

export default function AnalysisResultPanel({
  result,
  status,
  uploadSummary,
  selectedFile,
  isBusy,
  onRetry,
  onReset,
}: AnalysisResultPanelProps) {
  const [failedPreviewKey, setFailedPreviewKey] = useState<string | null>(null);
  const previewKey = selectedFile
    ? `${selectedFile.name}-${selectedFile.size}-${selectedFile.lastModified}`
    : null;
  const previewUrl = useMemo(
    () => (selectedFile ? URL.createObjectURL(selectedFile) : null),
    [selectedFile],
  );
  const scorePercent = result?.finalScore == null ? null : Math.round(result.finalScore * 100);
  const headline = getHeadline(result);
  const badgeTone = getBadgeTone(result?.status ?? status?.status ?? "processing");

  const chartData = useMemo(() => {
    if (!result?.chartData || result.chartData.labels.length === 0) return null;
    return {
      labels: result.chartData.labels,
      datasets: [
        {
          ...result.chartData.datasets[0],
          borderColor: "#6366f1",
          backgroundColor: "rgba(99, 102, 241, 0.1)",
          tension: 0.4,
          fill: true,
        },
        {
          ...result.chartData.datasets[1],
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          tension: 0.4,
          fill: true,
        },
      ],
    };
  }, [result?.chartData]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: { callback: (value: any) => `${value}%` },
      },
    },
    plugins: {
      legend: { position: "top" as const },
      tooltip: {
        callbacks: {
          label: (context: any) => `${context.dataset.label}: %${context.raw}`,
        },
      },
    },
  };

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return (
    <div className="space-y-6">

      {/* Başlık ve Job ID */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${badgeTone}`}>
            {headline.badge}
          </span>
          <div>
            <p className="text-2xl font-semibold text-slate-950">{headline.title}</p>
            <p className="mt-1 text-sm leading-7 text-slate-500">{headline.description}</p>
          </div>
        </div>
        <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-4 text-right">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">İş Kimliği</p>
          <p className="mt-2 max-w-[16rem] break-all font-mono text-sm text-slate-800">
            {uploadSummary?.jobId ?? status?.jobId ?? result?.jobId}
          </p>
        </div>
      </div>

      {/* Final Skor + Durum */}
      <div className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Deepfake Olasılığı</p>
          <p className="mt-3 text-4xl font-semibold text-slate-950">
            {scorePercent != null ? `%${scorePercent}` : "--"}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            {result?.finalLabel === "fake"
              ? "İçerik sahte olma yönünde güçlü sinyal veriyor."
              : result?.finalLabel === "real"
                ? "İçerik gerçek olma yönünde sinyal veriyor."
                : "Analiz henüz kesin bir karar üretemedi."}
          </p>
        </article>

        <article className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Analiz Durumu</p>
          <p className="mt-3 text-lg font-semibold text-slate-950">
            {status?.message ?? (result?.status === "failed" ? "Analiz tamamlanamadı" : "Analiz tamamlandı")}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Son güncelleme: {formatDate(result?.updatedAt ?? status?.updatedAt ?? null)}
          </p>
        </article>
      </div>

      {/* Modalite Skorları */}
      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Modalite Skorları</p>
            <p className="mt-1 text-sm text-slate-500">
              Görsel, ses ve metin kanallarının deepfake tespitine ayrı katkısı.
            </p>
          </div>
        </div>

        {result?.modalities.length ? (
          <div className="grid gap-3 sm:grid-cols-3">
            {result.modalities.map((modality) => {
              const modalityPercent = Math.round(modality.score * 100);
              const verdictLabel = getVerdictLabel(modality.verdict);
              const verdictColor = getVerdictColor(modality.verdict);
              const barColor = getBarColor(modality.verdict);

              return (
                <article key={modality.key} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900">{modality.label}</p>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${verdictColor}`}>
                      {verdictLabel}
                    </span>
                  </div>
                  <p className="mt-4 text-3xl font-semibold text-slate-950">%{modalityPercent}</p>
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-white">
                    <div
                      className={`h-full rounded-full transition-all ${barColor}`}
                      style={{ width: `${modalityPercent}%` }}
                    />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                      Güven %{Math.round(modality.confidence * 100)}
                    </p>
                    {modality.weight != null && (
                      <p className="text-xs text-slate-400">
                        Ağırlık %{Math.round(modality.weight * 100)}
                      </p>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="flex h-24 items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
            Modalite skoru bu analiz için henüz hesaplanmadı.
          </div>
        )}
      </div>

      {/* Trend Grafiği */}
      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="mb-4">
          <p className="text-sm font-semibold text-slate-900">Skor Dağılımı (Zaman Serisi)</p>
          <p className="mt-1 text-sm text-slate-500">
            Video süresi boyunca saniye bazlı deepfake olasılık değişimi.
          </p>
        </div>
        {chartData ? (
          <div className="h-[250px] w-full">
            <Line data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div className="flex h-[250px] items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
            Trend grafiği bu analiz için mevcut değil.
          </div>
        )}
      </div>

      {/* LLM Açıklaması */}
      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="mb-3 flex items-center gap-2">
          <p className="text-sm font-semibold text-slate-900">Sistem Açıklaması</p>
          <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
            Gemini LLM
          </span>
        </div>
        <p className="text-sm leading-7 text-slate-600">
          {result?.llmExplanation ?? "Bu analiz için açıklama metni henüz üretilmedi."}
        </p>
        <p className="mt-3 text-xs text-slate-400">
          Bu açıklama, görsel, ses ve metin analiz sonuçlarına dayanarak yapay zeka tarafından otomatik üretilmiştir.
          Kesin bir yargı değil, olasılık değerlendirmesidir.
        </p>
      </div>

      {/* Video Preview + Kaynak Bilgileri */}
      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-slate-200 bg-white p-5">
          <p className="text-sm font-semibold text-slate-900">Video Önizleme</p>
          <p className="mt-1 text-sm text-slate-500">
            Yüklenen kaynağın önizlemesi.
          </p>
          <div className="mt-4">
            {selectedFile && previewUrl && failedPreviewKey !== previewKey ? (
              <video
                key={previewKey ?? "preview"}
                controls
                preload="metadata"
                src={previewUrl}
                onError={() => setFailedPreviewKey(previewKey)}
                className="aspect-video w-full rounded-[24px] border border-slate-200 bg-slate-950 object-cover"
              />
            ) : (
              <div className="flex aspect-video items-center justify-center rounded-[24px] border border-dashed border-slate-200 bg-slate-50 px-6 text-center text-sm text-slate-500">
                {uploadSummary?.sourceType === "url"
                  ? "URL kaynağı için tarayıcı içinde güvenli önizleme sunulmuyor."
                  : "Önizleme oynatıcısı kullanılamadı. Dosya bilgileri aşağıda listeleniyor."}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-sm font-semibold text-slate-900">Kaynak Bilgileri</p>
          <div className="mt-4 space-y-4 text-sm text-slate-600">
            <MetadataRow label="Dosya Adı">
              {result?.videoMeta.filename ?? uploadSummary?.filename ?? selectedFile?.name ?? "Bulunamadı"}
            </MetadataRow>
            <MetadataRow label="Kaynak Tipi">
              {uploadSummary?.sourceType ?? result?.videoMeta.sourceType ?? "--"}
            </MetadataRow>
            <MetadataRow label="Dosya Boyutu">
              {formatFileSize(result?.videoMeta.fileSizeBytes ?? selectedFile?.size ?? null)}
            </MetadataRow>
            <MetadataRow label="Format">
              {result?.videoMeta.mimeType ?? selectedFile?.type ?? "--"}
            </MetadataRow>
            <MetadataRow label="Kaynak URL">
              {result?.videoMeta.sourceUrl ?? uploadSummary?.sourceUrl ?? "--"}
            </MetadataRow>
          </div>
        </div>
      </div>

      {/* Hata Mesajları */}
      {result?.errors.length ? (
        <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>{result.errors[0]}</div>
        </div>
      ) : null}

      {/* Aksiyon Butonları */}
      <div className="grid gap-3 sm:grid-cols-2">
        <button
          onClick={onReset}
          className="rounded-2xl border border-slate-200 bg-white py-3.5 text-sm font-semibold text-slate-800 transition hover:border-slate-300 hover:bg-slate-50"
        >
          Yeni Analiz Başlat
        </button>
        <button
          onClick={onRetry}
          disabled={isBusy || !status?.retryable}
          className="rounded-2xl bg-slate-900 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
        >
          Analizi Yeniden Dene
        </button>
      </div>
    </div>
  );
}

// ── Yardımcı Bileşenler ────────────────────────────────────────────────────

function MetadataRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-700">{children}</p>
    </div>
  );
}

// ── Yardımcı Fonksiyonlar ──────────────────────────────────────────────────

function getVerdictLabel(verdict: string): string {
  return { fake: "Sahte", real: "Gerçek", uncertain: "Belirsiz" }[verdict] ?? "Belirsiz";
}

function getVerdictColor(verdict: string): string {
  return {
    fake:      "bg-rose-100 text-rose-700",
    real:      "bg-emerald-100 text-emerald-700",
    uncertain: "bg-amber-100 text-amber-700",
  }[verdict] ?? "bg-slate-100 text-slate-600";
}

function getBarColor(verdict: string): string {
  return {
    fake:      "bg-rose-500",
    real:      "bg-emerald-500",
    uncertain: "bg-amber-400",
  }[verdict] ?? "bg-indigo-500";
}

function getHeadline(result: AnalysisResultViewModel | null) {
  if (!result) {
    return {
      badge: "Sonuç Bekleniyor",
      title: "Analiz sonucu hazırlanıyor",
      description: "Sistem bu iş için sonuç detaylarını toparlamaya devam ediyor.",
    };
  }
  if (result.status === "failed" || result.status === "expired") {
    return {
      badge: "Hata",
      title: "Analiz tamamlanamadı",
      description: "Kaynak veya işleme süresi nedeniyle sonuç üretilemedi.",
    };
  }
  return {
    badge: "Tamamlandı",
    title: "Analiz raporu hazır",
    description: "Deepfake olasılığı, modalite detayları ve sistem açıklaması aşağıda listelendi.",
  };
}

function getBadgeTone(status: string): string {
  if (status === "failed" || status === "expired") return "bg-rose-100 text-rose-700";
  if (status === "completed") return "bg-emerald-100 text-emerald-700";
  return "bg-indigo-100 text-indigo-700";
}

function formatDate(value: string | null): string {
  if (!value) return "--";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "--";
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function formatFileSize(value: number | null): string {
  if (value == null) return "--";
  return `${(value / 1024 / 1024).toFixed(2)} MB`;
}