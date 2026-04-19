export const ANALYSIS_ALLOWED_FILE_TYPES = [
  "video/mp4",
  "video/webm",
  "video/quicktime",
  "video/x-msvideo",
  "video/x-matroska",
] as const;

export const ANALYSIS_ALLOWED_FILE_EXTENSIONS = ".mp4,.webm,.mov,.avi,.mkv";
export const ANALYSIS_MAX_FILE_SIZE_MB = 500;
export const ANALYSIS_MAX_FILE_SIZE_BYTES = ANALYSIS_MAX_FILE_SIZE_MB * 1024 * 1024;

export const SUPPORTED_VIDEO_URL_PATTERN =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/watch|youtu\.be\/|tiktok\.com\/@[\w.]+\/video\/|instagram\.com\/(reel|p|tv)\/|twitter\.com\/\w+\/status\/|x\.com\/\w+\/status\/)[\w\-?=&%./]+/i;

export type JobStatus =
  | "uploaded"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "expired";

export type SourceType = "file" | "url";

export interface UploadResponseDto {
  jobId: string;
  videoId: string;
  status: JobStatus;
  message: string;
  sourceType: SourceType;
  filename?: string | null;
  sourceUrl?: string | null;
}

export interface JobStatusResponseDto {
  jobId: string;
  videoId: string;
  status: JobStatus;
  progress: number;
  retryable: boolean;
  message: string;
  sourceType: SourceType;
  updatedAt: string;
  filename?: string | null;
  sourceUrl?: string | null;
}

export interface ModalityScoreDto {
  key: "visual" | "audio" | "text";
  label: string;
  score: number;
  confidence: number;
  verdict: "fake" | "real" | "uncertain";
}

export interface ResultResponseDto {
  jobId: string;
  videoId: string;
  status: JobStatus;
  finalScore?: number | null;
  finalLabel?: "fake" | "real" | "uncertain" | null;
  llmExplanation?: string | null;
  modalities: ModalityScoreDto[];
  videoMeta: {
    filename?: string | null;
    sourceType: SourceType;
    sourceUrl?: string | null;
    mimeType?: string | null;
    fileSizeBytes?: number | null;
    durationSeconds?: number | null;
  };
  errors: string[];
  updatedAt: string;
}

export interface UploadSummary {
  jobId: string;
  videoId: string;
  message: string;
  sourceType: SourceType;
  filename?: string;
  sourceUrl?: string;
}

export interface AnalysisStatus {
  jobId: string;
  videoId: string;
  status: JobStatus;
  progress: number;
  retryable: boolean;
  message: string;
  updatedAt: string;
  sourceType: SourceType;
  filename?: string;
  sourceUrl?: string;
}

export interface AnalysisResultViewModel {
  jobId: string;
  videoId: string;
  status: JobStatus;
  finalScore: number | null;
  finalLabel: "fake" | "real" | "uncertain" | null;
  llmExplanation: string | null;
  modalities: ModalityScoreDto[];
  updatedAt: string;
  errors: string[];
  videoMeta: {
    filename?: string;
    sourceType: SourceType;
    sourceUrl?: string;
    mimeType?: string;
    fileSizeBytes?: number;
    durationSeconds?: number;
  };
}

export function getPollingDelay(attempt: number): number {
  if (attempt < 12) {
    return 2500;
  }
  if (attempt < 20) {
    return 5000;
  }
  return 10000;
}
