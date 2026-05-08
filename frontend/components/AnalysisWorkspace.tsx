"use client";

import { useState } from "react";
import AnalysisResultPanel from "@/components/AnalysisResultPanel";
import VideoLinkInput from "@/components/VideoLinkInput";
import VideoUpload from "@/components/VideoUpload";
import { useAnalysisFlow } from "@/hooks/useAnalysisFlow";

type Tab = "file" | "url";

export default function AnalysisWorkspace() {
  const [activeTab, setActiveTab] = useState<Tab>("file");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const {
    error,
    isBusy,
    phase,
    progress,
    result,
    status,
    uploadSummary,
    reset,
    retryFailedAnalysis,
    startFileUpload,
    startUrlUpload,
  } = useAnalysisFlow();

  async function handleFileUpload() {
    if (!selectedFile) return;
    await startFileUpload(selectedFile);
  }

  async function handleUrlUpload(url: string) {
    await startUrlUpload(url);
  }

  function handleReset() {
    setSelectedFile(null);
    reset();
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
      <section className="space-y-6">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
          <span className="h-2 w-2 rounded-full bg-indigo-500" />
          Çok modlu ön inceleme akışı
        </div>

        <div className="space-y-4">
          <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
            İçeriği sisteme gönderin, analiz kuyruğunu hemen başlatalım.
          </h1>
          <p className="max-w-xl text-base leading-8 text-slate-600">
            Bu ekranda ister doğrudan video dosyası yükleyebilir ister sosyal
            medya bağlantısı göndererek inceleme sürecini başlatabilirsiniz.
            Sistem yükleme sonrası durumu otomatik takip eder, sonucu hazır
            olduğunda final skorları ve açıklamayı gösterir.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <article className="rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-slate-900">Dosya yükleme</p>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              MP4, WebM, MOV, AVI ve MKV formatlarını kabul eder. Büyük dosyalar
              için istemci ve backend tarafında ortak doğrulama uygulanır.
            </p>
          </article>
          <article className="rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-slate-900">Bağlantı analizi</p>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              YouTube, TikTok, Instagram ve X bağlantıları tek alan üzerinden
              doğrulanır, kuyruğa alınır ve durum polling ile izlenir.
            </p>
          </article>
        </div>
      </section>

      <section>
        <div className="overflow-hidden rounded-[36px] border border-white/70 bg-white/88 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur">
          <div className="border-b border-slate-100 px-6 py-6">
            <p className="text-sm font-medium text-slate-500">Analiz başlat</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">
              Video veya bağlantı gönderin
            </h2>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              İçerik önce yükleme kuyruğuna alınır, ardından analiz adımları
              sistem tarafında ilerler.
            </p>
          </div>

          <div className="space-y-6 px-6 py-6">
            {result || (phase === "failed" && (uploadSummary || status)) ? (
              <AnalysisResultPanel
                result={result}
                status={status}
                uploadSummary={uploadSummary}
                selectedFile={selectedFile}
                isBusy={isBusy}
                onRetry={retryFailedAnalysis}
                onReset={handleReset}
              />
            ) : (
              <>
                <div className="grid grid-cols-2 gap-2 rounded-[22px] bg-slate-100 p-1">
                  <button
                    onClick={() => {
                      setActiveTab("file");
                    }}
                    disabled={isBusy}
                    className={`rounded-[18px] px-4 py-3 text-sm font-medium transition ${
                      activeTab === "file"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    } disabled:opacity-60`}
                  >
                    Dosya yükle
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab("url");
                    }}
                    disabled={isBusy}
                    className={`rounded-[18px] px-4 py-3 text-sm font-medium transition ${
                      activeTab === "url"
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500 hover:text-slate-700"
                    } disabled:opacity-60`}
                  >
                    Bağlantı ekle
                  </button>
                </div>

                {activeTab === "file" ? (
                  <div className="space-y-4">
                    <VideoUpload
                      onFileSelect={setSelectedFile}
                      onClear={() => setSelectedFile(null)}
                      isLoading={isBusy}
                      selectedFile={selectedFile}
                    />
                    <button
                      onClick={handleFileUpload}
                      disabled={!selectedFile || isBusy}
                      className="w-full rounded-2xl bg-slate-900 py-3.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
                    >
                      {isBusy ? "İşlem sürüyor..." : "Dosyayı incelemeye gönder"}
                    </button>
                  </div>
                ) : (
                  <VideoLinkInput onUrlSubmit={handleUrlUpload} isLoading={isBusy} />
                )}

                {isBusy && (
                  <div className="rounded-[24px] border border-indigo-100 bg-indigo-50 px-4 py-4">
                    <div className="mb-2 flex items-center justify-between text-xs font-medium text-indigo-700">
                      <span>
                        {phase === "uploading" ? "Yükleme sürüyor" : status?.message ?? "Analiz durumu izleniyor"}
                      </span>
                      <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white">
                      <div
                        className="h-full rounded-full bg-indigo-500 transition-all duration-300 ease-out"
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    <div className="mt-4 grid gap-3 text-sm text-indigo-900 sm:grid-cols-2">
                      <div className="rounded-2xl bg-white/80 px-4 py-3">
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-indigo-400">
                          Job ID
                        </p>
                        <p className="mt-1 break-all font-mono text-sm text-slate-700">
                          {uploadSummary?.jobId ?? "--"}
                        </p>
                      </div>
                      <div className="rounded-2xl bg-white/80 px-4 py-3">
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-indigo-400">
                          Durum
                        </p>
                        <p className="mt-1 text-sm text-slate-700">
                          {status?.status ?? "uploading"}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <span className="font-medium">Hata:</span> {error}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
