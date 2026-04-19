"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  AnalysisResultViewModel,
  AnalysisStatus,
  JobStatus,
  UploadSummary,
  getPollingDelay,
} from "@/lib/analysis-contract";
import { mapResultResponse, mapStatusResponse, mapUploadResponse } from "@/lib/analysis-mappers";
import {
  getAnalysisResult,
  getAnalysisStatus,
  retryAnalysis,
  uploadVideo,
  uploadVideoByUrl,
} from "@/lib/api";

type FlowPhase = "idle" | "uploading" | "polling" | "completed" | "failed";

interface AnalysisFlowState {
  phase: FlowPhase;
  progress: number;
  error: string | null;
  uploadSummary: UploadSummary | null;
  status: AnalysisStatus | null;
  result: AnalysisResultViewModel | null;
}

const initialState: AnalysisFlowState = {
  phase: "idle",
  progress: 0,
  error: null,
  uploadSummary: null,
  status: null,
  result: null,
};

export function useAnalysisFlow() {
  const [state, setState] = useState<AnalysisFlowState>(initialState);
  const pollingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeJobIdRef = useRef<string | null>(null);

  const clearPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => clearPolling, [clearPolling]);

  const hydrateCompletedResult = useCallback(async (jobId: string) => {
    const result = mapResultResponse(await getAnalysisResult(jobId));
    setState((current) => ({
      ...current,
      phase: result.status === "completed" ? "completed" : "failed",
      progress: 100,
      result,
      error: result.errors[0] ?? null,
    }));
  }, []);

  const pollUntilSettled = useCallback(async (jobId: string, attempt = 0) => {
    activeJobIdRef.current = jobId;

    try {
      const status = mapStatusResponse(await getAnalysisStatus(jobId));
      setState((current) => ({
        ...current,
        phase: "polling",
        status,
        progress: status.progress,
        error: null,
      }));

      if (isTerminalStatus(status.status)) {
        clearPolling();
        await hydrateCompletedResult(jobId);
        return;
      }

      // Ilk denemeler daha sik, sonra daha seyrek; uzun analizlerde gereksiz istek atmayiz.
      pollingTimeoutRef.current = setTimeout(() => {
        void pollUntilSettled(jobId, attempt + 1);
      }, getPollingDelay(attempt));
    } catch (error) {
      clearPolling();
      setState((current) => ({
        ...current,
        phase: "failed",
        error: error instanceof Error ? error.message : "Durum sorgulanırken bir hata oluştu.",
      }));
    }
  }, [clearPolling, hydrateCompletedResult]);

  const beginFlow = useCallback(async (uploadPromise: Promise<UploadSummary>) => {
    clearPolling();
    setState({
      phase: "uploading",
      progress: 8,
      error: null,
      uploadSummary: null,
      status: null,
      result: null,
    });

    try {
      const uploadSummary = await uploadPromise;
      setState((current) => ({
        ...current,
        phase: "polling",
        uploadSummary,
        progress: 15,
      }));
      await pollUntilSettled(uploadSummary.jobId);
    } catch (error) {
      setState((current) => ({
        ...current,
        phase: "failed",
        progress: 0,
        error: error instanceof Error ? error.message : "Yukleme basarisiz oldu.",
      }));
    }
  }, [clearPolling, pollUntilSettled]);

  const startFileUpload = useCallback(async (file: File) => {
    await beginFlow(uploadVideo(file).then(mapUploadResponse));
  }, [beginFlow]);

  const startUrlUpload = useCallback(async (url: string) => {
    await beginFlow(uploadVideoByUrl(url).then(mapUploadResponse));
  }, [beginFlow]);

  const retryFailedAnalysis = useCallback(async () => {
    const jobId = activeJobIdRef.current ?? state.uploadSummary?.jobId;
    if (!jobId) {
      return;
    }

    await beginFlow(retryAnalysis(jobId).then(mapUploadResponse));
  }, [beginFlow, state.uploadSummary?.jobId]);

  const reset = useCallback(() => {
    clearPolling();
    activeJobIdRef.current = null;
    setState(initialState);
  }, [clearPolling]);

  return {
    ...state,
    isBusy: state.phase === "uploading" || state.phase === "polling",
    startFileUpload,
    startUrlUpload,
    retryFailedAnalysis,
    reset,
  };
}

function isTerminalStatus(status: JobStatus): boolean {
  return status === "completed" || status === "failed" || status === "expired";
}
