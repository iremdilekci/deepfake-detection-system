const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UploadResponse {
  job_id: string;
  message: string;
  filename?: string;
  source_url?: string;
}

export interface ApiError {
  detail: string;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/upload-video`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err: ApiError = await response.json().catch(() => ({
      detail: "Sunucu hatası oluştu.",
    }));
    throw new Error(err.detail ?? "Yükleme başarısız oldu.");
  }

  return response.json();
}

export async function uploadVideoByUrl(url: string): Promise<UploadResponse> {
  const response = await fetch(`${API_URL}/upload-video-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const err: ApiError = await response.json().catch(() => ({
      detail: "Sunucu hatası oluştu.",
    }));
    throw new Error(err.detail ?? "Yükleme başarısız oldu.");
  }

  return response.json();
}
