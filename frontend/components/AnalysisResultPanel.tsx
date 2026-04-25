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
    
    // API'den standart Dataset/Labels formatında geliyor, sadece UI renklerini inject ediyoruz
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
        ticks: {
          callback: (value: any) => `${value}%`,
        },
      },
    },
    plugins: {
      legend: {
        position: "top" as const,
      },
      tooltip: {
        callbacks: {
          label: (context: any) => `${context.dataset.label}: %${context.raw}`,
        },
      },
    },
  };

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <div className="space-y-6">
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
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Job ID</p>
          <p className="mt-2 max-w-[16rem] break-all font-mono text-sm text-slate-800">
            {uploadSummary?.jobId ?? status?.jobId ?? result?.jobId}
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <article className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Final skor</p>
          <p className="mt-3 text-4xl font-semibold text-slate-950">
            {scorePercent != null ? `%${scorePercent}` : "--"}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            {result?.finalLabel === "fake"
              ? "Icerik sahte olma yonunde sinyal veriyor."
              : result?.finalLabel === "real"
                ? "Icerik gercek olma yonunde sinyal veriyor."
                : "Analiz henüz kesin bir etiket üretmedi."}
          </p>
        </article>

        <article className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">Durum</p>
          <p className="mt-3 text-lg font-semibold text-slate-950">
            {status?.message ?? (result?.status === "failed" ? "Analiz tamamlanamadi" : "Analiz tamamlandi")}
          </p>
          <p className="mt-2 text-sm text-slate-500">
            Son guncelleme: {formatDate(result?.updatedAt ?? status?.updatedAt ?? null)}
          </p>
        </article>
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-900">Modalite skorlari</p>
            <p className="mt-1 text-sm text-slate-500">Gorsel, ses ve metin kanallarinin ayri katkisi.</p>
          </div>
        </div>

        {result?.modalities.length ? (
          <div className="grid gap-3 sm:grid-cols-3">
            {result.modalities.map((modality) => {
              const modalityPercent = Math.round(modality.score * 100);
              return (
                <article key={modality.key} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-slate-900">{modality.label}</p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-500">
                      {modality.verdict}
                    </span>
                  </div>
                  <p className="mt-4 text-3xl font-semibold text-slate-950">%{modalityPercent}</p>
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-white">
                    <div
                      className="h-full rounded-full bg-indigo-500 transition-all"
                      style={{ width: `${modalityPercent}%` }}
                    />
                  </div>
                  <p className="mt-3 text-xs uppercase tracking-[0.16em] text-slate-400">
                    Guven {Math.round(modality.confidence * 100)}%
                  </p>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <div className="mb-4">
          <p className="text-sm font-semibold text-slate-900">Skor Dagilimi (Trend)</p>
          <p className="mt-1 text-sm text-slate-500">Video suresince saniye bazli deepfake olasilik degisimi.</p>
        </div>
        
        {chartData ? (
          <div className="h-[250px] w-full">
            <Line data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div className="flex h-[250px] items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
            Trend grafigi bu analiz icin mevcut degil.
          </div>
        )}
      </div>

      <div className="rounded-[28px] border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-900">LLM aciklamasi</p>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          {result?.llmExplanation ?? "Bu analiz icin aciklama metni henuz uretilmedi."}
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[28px] border border-slate-200 bg-white p-5">
          <p className="text-sm font-semibold text-slate-900">Video preview</p>
          <p className="mt-1 text-sm text-slate-500">
            Yuklenen kaynagin onizlemesi veya oyuncu fallback bilgisi.
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
                  ? "URL kaynagi icin tarayici icinde guvenli preview sunulmuyor; kaynak baglanti asagida listelendi."
                  : "Onizleme oynaticisi kullanilamadi. Dosya bilgileri fallback olarak gosteriliyor."}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-5">
          <p className="text-sm font-semibold text-slate-900">Kaynak bilgileri</p>
          <div className="mt-4 space-y-4 text-sm text-slate-600">
            <MetadataRow label="Dosya">
              {result?.videoMeta.filename ?? uploadSummary?.filename ?? selectedFile?.name ?? "Bulunamadi"}
            </MetadataRow>
            <MetadataRow label="Kaynak tipi">{uploadSummary?.sourceType ?? result?.videoMeta.sourceType ?? "--"}</MetadataRow>
            <MetadataRow label="Boyut">
              {formatFileSize(result?.videoMeta.fileSizeBytes ?? selectedFile?.size ?? null)}
            </MetadataRow>
            <MetadataRow label="Mime type">{result?.videoMeta.mimeType ?? selectedFile?.type ?? "--"}</MetadataRow>
            <MetadataRow label="Kaynak URL">{result?.videoMeta.sourceUrl ?? uploadSummary?.sourceUrl ?? "--"}</MetadataRow>
          </div>
        </div>
      </div>

      {result?.errors.length ? (
        <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>{result.errors[0]}</div>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <button
          onClick={onReset}
          className="rounded-2xl border border-slate-200 bg-white py-3.5 text-sm font-semibold text-slate-800 transition hover:border-slate-300 hover:bg-slate-50"
        >
          Yeni analiz baslat
        </button>

        <button
          onClick={onRetry}
          disabled={isBusy || !status?.retryable}
          className="rounded-2xl bg-slate-900 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
        >
          Analizi yeniden dene
        </button>
      </div>
    </div>
  );
}

function MetadataRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-700">{children}</p>
    </div>
  );
}

function getHeadline(result: AnalysisResultViewModel | null) {
  if (!result) {
    return {
      badge: "Sonuc bekleniyor",
      title: "Analiz sonucu hazirlaniyor",
      description: "Sistem bu is icin sonuc detaylarini toparliyor.",
    };
  }

  if (result.status === "failed" || result.status === "expired") {
    return {
      badge: "Hata",
      title: "Analiz tamamlanamadi",
      description: "Kaynak veya isleme suresi nedeniyle sonuc uretemedik.",
    };
  }

  return {
    badge: "Tamamlandi",
    title: "Analiz raporu hazir",
    description: "Final skor, modalite detaylari ve aciklama asagida listelendi.",
  };
}

function getBadgeTone(status: string) {
  if (status === "failed" || status === "expired") {
    return "bg-rose-100 text-rose-700";
  }
  if (status === "completed") {
    return "bg-emerald-100 text-emerald-700";
  }
  return "bg-indigo-100 text-indigo-700";
}

function formatDate(value: string | null): string {
  if (!value) {
    return "--";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "--";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function formatFileSize(value: number | null): string {
  if (value == null) {
    return "--";
  }
  return `${(value / 1024 / 1024).toFixed(2)} MB`;
}
