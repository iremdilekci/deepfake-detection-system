import {
  JobStatusResponseDto,
  ResultResponseDto,
  UploadResponseDto,
} from "@/lib/analysis-contract";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiError {
  detail?: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  return response.json() as Promise<T>;
}

async function parseError(response: Response): Promise<Error> {
  const err = await response.json().catch(() => ({ detail: "Sunucu hatası oluştu." })) as ApiError;
  return new Error(err.detail ?? "İşlem başarısız oldu.");
}

export async function uploadVideo(file: File): Promise<UploadResponseDto> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/upload-video`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJson<UploadResponseDto>(response);
}

export async function uploadVideoByUrl(url: string): Promise<UploadResponseDto> {
  const response = await fetch(`${API_URL}/upload-video-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJson<UploadResponseDto>(response);
}

export async function retryAnalysis(jobId: string): Promise<UploadResponseDto> {
  const response = await fetch(`${API_URL}/analyze/${jobId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ retryFailed: true }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJson<UploadResponseDto>(response);
}

export async function getAnalysisStatus(jobId: string): Promise<JobStatusResponseDto> {
  const response = await fetch(`${API_URL}/jobs/${jobId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJson<JobStatusResponseDto>(response);
}

export async function getAnalysisResult(jobId: string): Promise<ResultResponseDto> {
  const response = await fetch(`${API_URL}/results/${jobId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return parseJson<ResultResponseDto>(response);
}
