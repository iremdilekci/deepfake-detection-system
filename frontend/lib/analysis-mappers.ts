import {
  AnalysisResultViewModel,
  AnalysisStatus,
  JobStatusResponseDto,
  ResultResponseDto,
  UploadResponseDto,
  UploadSummary,
} from "@/lib/analysis-contract";

export function mapUploadResponse(dto: UploadResponseDto): UploadSummary {
  return {
    jobId: dto.jobId,
    videoId: dto.videoId,
    message: dto.message,
    sourceType: dto.sourceType,
    filename: dto.filename ?? undefined,
    sourceUrl: dto.sourceUrl ?? undefined,
  };
}

export function mapStatusResponse(dto: JobStatusResponseDto): AnalysisStatus {
  return {
    jobId: dto.jobId,
    videoId: dto.videoId,
    status: dto.status,
    progress: dto.progress,
    retryable: dto.retryable,
    message: dto.message,
    updatedAt: dto.updatedAt,
    sourceType: dto.sourceType,
    filename: dto.filename ?? undefined,
    sourceUrl: dto.sourceUrl ?? undefined,
  };
}

export function mapResultResponse(dto: ResultResponseDto): AnalysisResultViewModel {
  return {
    jobId: dto.jobId,
    videoId: dto.videoId,
    status: dto.status,
    finalScore: dto.finalScore ?? null,
    finalLabel: dto.finalLabel ?? null,
    llmExplanation: dto.llmExplanation ?? null,
    modalities: dto.modalities,
    updatedAt: dto.updatedAt,
    errors: dto.errors,
    videoMeta: {
      filename: dto.videoMeta.filename ?? undefined,
      sourceType: dto.videoMeta.sourceType,
      sourceUrl: dto.videoMeta.sourceUrl ?? undefined,
      mimeType: dto.videoMeta.mimeType ?? undefined,
      fileSizeBytes: dto.videoMeta.fileSizeBytes ?? undefined,
      durationSeconds: dto.videoMeta.durationSeconds ?? undefined,
    },
  };
}
