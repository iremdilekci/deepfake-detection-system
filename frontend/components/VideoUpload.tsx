"use client";

import { useRef, useState, DragEvent, ChangeEvent } from "react";

const ACCEPTED_TYPES = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/x-matroska"];
const ACCEPTED_EXTENSIONS = ".mp4,.webm,.mov,.avi,.mkv";
const MAX_SIZE_MB = 500;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface VideoUploadProps {
  onFileSelect: (file: File) => void;
  onClear: () => void;
  isLoading: boolean;
  selectedFile: File | null;
}

export default function VideoUpload({
  onFileSelect,
  onClear,
  isLoading,
  selectedFile,
}: VideoUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validate(file: File): string | null {
    if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(mp4|webm|mov|avi|mkv)$/i)) {
      return `Desteklenmeyen dosya tipi. Kabul edilenler: MP4, WebM, MOV, AVI, MKV`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `Dosya boyutu çok büyük. Maksimum: ${MAX_SIZE_MB} MB (Seçilen: ${(file.size / 1024 / 1024).toFixed(1)} MB)`;
    }
    return null;
  }

  function handleFile(file: File) {
    const validationError = validate(file);
    if (validationError) {
      setError(validationError);
      onClear();
      return;
    }
    setError(null);
    onFileSelect(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragLeave() {
    setDragging(false);
  }

  function handleClear() {
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
    onClear();
  }

  return (
    <div className="w-full">
      <div
        onClick={() => !isLoading && inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative overflow-hidden rounded-[28px] border border-dashed transition-all cursor-pointer select-none
          ${dragging
            ? "border-indigo-400 bg-indigo-50 shadow-[0_20px_60px_rgba(99,102,241,0.14)]"
            : selectedFile
              ? "border-emerald-300 bg-emerald-50 shadow-[0_20px_60px_rgba(16,185,129,0.12)]"
              : "border-slate-200 bg-white hover:border-indigo-200 hover:shadow-[0_20px_60px_rgba(15,23,42,0.08)]"
          }
          ${isLoading ? "pointer-events-none opacity-60" : ""}
        `}
      >
        <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-slate-50 to-transparent" />
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS}
          className="hidden"
          onChange={handleChange}
          disabled={isLoading}
        />

        {selectedFile ? (
          <div className="relative flex min-h-56 flex-col items-center justify-center gap-4 px-6 py-10 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600">
              <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-900">{selectedFile.name}</p>
              <p className="mt-1 text-sm text-slate-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700">
              Dosya hazır
            </div>
            {!isLoading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="text-sm text-slate-500 transition-colors hover:text-rose-500"
              >
                Dosyayı kaldır
              </button>
            )}
          </div>
        ) : (
          <div className="relative flex min-h-56 flex-col items-center justify-center gap-4 px-6 py-10 text-center">
            <div
              className={`flex h-16 w-16 items-center justify-center rounded-2xl transition-colors ${
                dragging ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-500"
              }`}
            >
              <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-base font-semibold text-slate-900">
                {dragging ? "Dosyayı buraya bırakın" : "Video dosyanızı buraya bırakın"}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                veya bilgisayarınızdan seçin
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500">
              <span className="rounded-full bg-slate-100 px-3 py-1">MP4</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">WebM</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">MOV</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">AVI</span>
              <span className="rounded-full bg-slate-100 px-3 py-1">MKV</span>
            </div>
            <p className="text-xs text-slate-400">Maksimum dosya boyutu {MAX_SIZE_MB} MB</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
