"use client";

import { useState, ChangeEvent } from "react";

const URL_PATTERN =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|tiktok\.com\/@[\w.]+\/video\/|instagram\.com\/(reel|p|tv)\/|twitter\.com\/\w+\/status\/|x\.com\/\w+\/status\/)[\w\-?=&%./]+/i;

interface VideoLinkInputProps {
  onUrlSubmit: (url: string) => void;
  isLoading: boolean;
}

export default function VideoLinkInput({ onUrlSubmit, isLoading }: VideoLinkInputProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  function validate(value: string): string | null {
    if (!value.trim()) return "URL boş bırakılamaz.";
    if (!URL_PATTERN.test(value.trim())) {
      return "Geçerli bir YouTube, TikTok, Instagram, Twitter/X video linki girin.";
    }
    return null;
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setUrl(value);
    if (touched) {
      setError(validate(value));
    }
  }

  function handleBlur() {
    setTouched(true);
    setError(validate(url));
  }

  function handleSubmit() {
    setTouched(true);
    const validationError = validate(url);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    onUrlSubmit(url.trim());
  }

  const isValid = touched && !error && url.trim().length > 0;

  return (
    <div className="flex w-full flex-col gap-4">
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-800">Video bağlantısı</p>
        <p className="text-sm text-slate-500">
          Sosyal medya paylaşım linkini ekleyin, biz analizi kuyruklayalım.
        </p>
      </div>
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-4 flex items-center">
          <svg className="h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        </div>
        <input
          type="url"
          value={url}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={isLoading}
          placeholder="https://www.youtube.com/watch?v=..."
          className={`
            w-full rounded-2xl border bg-white py-4 pl-11 pr-4 text-sm text-slate-800
            outline-none transition-all placeholder:text-slate-400
            disabled:opacity-60 disabled:cursor-not-allowed
            ${error
              ? "border-rose-300 focus:border-rose-400"
              : isValid
                ? "border-emerald-300 focus:border-emerald-400"
                : "border-slate-200 focus:border-indigo-300"
            }
          `}
        />
        {isValid && (
          <div className="pointer-events-none absolute inset-y-0 right-4 flex items-center">
            <svg className="h-4 w-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          <svg className="mt-0.5 h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        {["YouTube", "TikTok", "Instagram", "Twitter/X"].map((platform) => (
          <span key={platform} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5">
            {platform}
          </span>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={isLoading || !url.trim()}
        className="w-full rounded-2xl bg-slate-900 py-3.5 text-sm font-semibold text-white transition-all hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
      >
        Bağlantıyı incelemeye gönder
      </button>
    </div>
  );
}
