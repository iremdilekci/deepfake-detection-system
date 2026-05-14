import json
import os
import shutil
import subprocess
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import librosa
import mediapipe as mp
import numpy as np
from scipy.signal import butter, sosfilt, correlate
from scipy.stats import pearsonr
from moviepy.editor import VideoFileClip

warnings.filterwarnings("ignore")

# Ses/video hızı: VERADEEP_SES_FRAME_STRIDE (varsayılan 2), VERADEEP_SES_MAX_SANIYE (0=tümü)
# Ses çıkarma: ffmpeg varsa MoviePy'den hızlı


def _wav_cikar_ffmpeg(video_path: str, wav_path: str, sr: int = 16000) -> bool:
    exe = shutil.which("ffmpeg")
    if not exe:
        return False
    try:
        subprocess.run(
            [
                exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                str(sr),
                "-f",
                "wav",
                wav_path,
            ],
            check=True,
            timeout=7200,
        )
        return Path(wav_path).is_file() and Path(wav_path).stat().st_size > 0
    except (subprocess.CalledProcessError, OSError, subprocess.TimeoutExpired):
        return False


# ===========================================================================
# 1. BÖLÜM: VERİ YAPILARI
# ===========================================================================
@dataclass
class FrameFeatures:
    frame_index: int
    timestamp_sec: float
    mar: float
    mar_delta: float
    face_detected: bool

@dataclass
class AudioFeatures:
    rms_energy: np.ndarray
    speech_mask: np.ndarray
    sample_rate: int
    noise_level: str

@dataclass
class SyncReport:
    primary_speaker_confidence: float
    background_noise_level: str
    sync_lag_compensation: int
    final_risk_score: float
    detected_scenario: str
    frame_level_anomalies: list

# ===========================================================================
# 2. BÖLÜM: SES SİNYALİ İŞLEME
# ===========================================================================
class AudioPreprocessor:
    """Sesi frekanslarına ayırıp insan sesi enerjisini (RMS) hesaplar."""
    def __init__(self, sample_rate=16000):
        self.sr = sample_rate

    def extract(self, audio_path: str) -> AudioFeatures:
        max_sec = os.environ.get("VERADEEP_SES_MAX_SANIYE", "0").strip()
        duration = None
        try:
            d = float(max_sec.replace(",", "."))
            if d > 0:
                duration = d
        except ValueError:
            pass
        raw, sr = librosa.load(audio_path, sr=self.sr, mono=True, duration=duration)

        # 1. Pre-emphasis
        pre = librosa.effects.preemphasis(raw, coef=0.97)

        # 2. Bandpass: İnsan konuşma frekansları 100-4000 Hz
        nyq = sr / 2.0
        sos = butter(4, [100 / nyq, 4000 / nyq], btype="band", output="sos")
        vocal = sosfilt(sos, pre)

        # 3. RMS hesapla
        hop = 256
        rms = librosa.feature.rms(y=vocal, hop_length=hop)[0]

        # 4. Adaptive Noise Gate
        rms_thresh = np.percentile(rms, 25)
        clean_rms = rms.copy()
        clean_rms[clean_rms < rms_thresh] *= 0.3

        # 5. Gürültü seviyesi
        speech_ratio = np.sum(clean_rms > 0) / (len(clean_rms) + 1e-9)
        noise_level = "low" if speech_ratio > 0.5 else ("medium" if speech_ratio > 0.25 else "high")

        mask = (clean_rms > 0).astype(int)

        # === YENİ: Akustik Doğallık Özellikleri ===
        # A. Spectral Flatness — AI sesleri düz (robotik), gerçek ses dinamik
        spec_flatness = librosa.feature.spectral_flatness(y=vocal, hop_length=hop)[0]
        self.avg_flatness = float(np.mean(spec_flatness))  # Yüksek = daha robotik

        # B. MFCC Varyansı — Gerçek seste MFCC'ler sürekli değişir, AI'da monoton
        mfcc = librosa.feature.mfcc(y=vocal, sr=sr, n_mfcc=13, hop_length=hop)
        self.mfcc_variance = float(np.mean(np.var(mfcc, axis=1)))  # Düşük = monoton = AI

        # C. Zero Crossing Rate — Doğal seste ritmik, AI'da düzensiz
        zcr = librosa.feature.zero_crossing_rate(y=vocal, hop_length=hop)[0]
        self.zcr_std = float(np.std(zcr))  # Yüksek std = düzensiz = AI şüphesi

        return AudioFeatures(rms_energy=clean_rms, speech_mask=mask, sample_rate=sr, noise_level=noise_level)

# ===========================================================================
# 3. BÖLÜM: DUDAK (MAR) İŞLEME
# ===========================================================================
class FacialLandmarkExtractor:
    """Videodaki dudak hareketlerini (MAR) kare kare sayısallaştırır."""
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
        )

    def process_video(self, video_path: str) -> list:
        raw_stride = os.environ.get("VERADEEP_SES_FRAME_STRIDE", "2").strip()
        frame_stride = max(1, int(raw_stride)) if raw_stride.isdigit() else 2

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        features, prev_mar, frame_idx = [], 0.0, 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_stride != 0:
                frame_idx += 1
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.face_mesh.process(rgb)

            if result.multi_face_landmarks:
                lms = result.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]

                # Dudak açıklık oranı (MAR) — üst ve alt dudak merkez noktaları
                upper = np.mean([[lms[i].x * w, lms[i].y * h] for i in [13, 312, 311, 310, 415, 308]], axis=0)
                lower = np.mean([[lms[i].x * w, lms[i].y * h] for i in [14, 317, 402, 318, 324, 78]], axis=0)
                mouth_w = np.linalg.norm([
                    lms[308].x * w - lms[78].x * w,
                    lms[308].y * h - lms[78].y * h
                ])
                mar = float(np.linalg.norm(lower - upper) / (mouth_w + 1e-6))

                features.append(FrameFeatures(frame_idx, frame_idx / fps, mar, abs(mar - prev_mar), True))
                prev_mar = mar
            else:
                features.append(FrameFeatures(frame_idx, frame_idx / fps, 0.0, 0.0, False))
            frame_idx += 1

        cap.release()
        return features

# ===========================================================================
# 4. BÖLÜM: SENKRONİZASYON ANALİZİ
# ===========================================================================
class SyncAnalyzer:
    """Ses enerjisi ile dudak hareketini karşılaştırarak senkron kalitesini ölçer."""

    def compute_sync_score(self, audio_rms: np.ndarray, mar_values: np.ndarray) -> dict:
        length = min(len(audio_rms), len(mar_values))
        a = audio_rms[:length].copy()
        m = mar_values[:length].copy()

        # Minimum veri kontrolü
        if length < 20:
            return {"best_lag_frames": 0, "correlation_score": 0.5, "lag_jitter": 0, "risk_score_calculated": 50.0}

        # --- A. Global Pearson Korelasyonu ---
        # Sinyal Yumuşatma (Smoothing): Jitter etkisini azaltmak için 3 karelik hareketli ortalama
        if length > 5:
            a = np.convolve(a, np.ones(3)/3, mode='same')
            m = np.convolve(m, np.ones(3)/3, mode='same')

        # Tüm sinyali normalize et (std=0 durumunu ele al)
        a_std = a.std()
        m_std = m.std()

        if a_std < 1e-4 or m_std < 1e-4:
            # Sinyal çok zayıf — belirsiz dön (Gerçek videolarda da sessizlik olabilir)
            return {"best_lag_frames": 0, "correlation_score": 0.6, "lag_jitter": 0, "risk_score_calculated": 30.0}

        a_norm = (a - a.mean()) / (a_std + 1e-6)
        m_norm = (m - m.mean()) / (m_std + 1e-6)

        # Çapraz korelasyon ile en iyi lag'i bul (± 15 kare)
        max_lag = min(15, length // 4)
        corr_vals = []
        lag_range = range(-max_lag, max_lag + 1)
        for lag in lag_range:
            if lag > 0:
                r = np.corrcoef(a_norm[lag:], m_norm[:-lag])[0, 1] if lag < length else 0
            elif lag < 0:
                r = np.corrcoef(a_norm[:lag], m_norm[-lag:])[0, 1] if -lag < length else 0
            else:
                r = np.corrcoef(a_norm, m_norm)[0, 1]
            corr_vals.append(r if np.isfinite(r) else 0)

        best_idx = int(np.argmax(corr_vals))
        best_lag = list(lag_range)[best_idx]
        global_corr = corr_vals[best_idx]

        # --- B. Kaymalı Pencere Analizi (Temporal Consistency) ---
        # Adaptif pencere boyutu: Video uzunluğunun %15'i, min 10 kare
        win = max(10, length // 7)
        step = max(5, win // 2)

        window_corrs = []
        window_lags = []

        for start in range(0, length - win, step):
            a_w = a_norm[start:start + win]
            m_w = m_norm[start:start + win]

            if a_w.std() < 1e-8 or m_w.std() < 1e-8:
                continue

            # Pencere içi en iyi lag
            best_r = -1
            best_l = 0
            for lag in range(-min(5, win//4), min(5, win//4) + 1):
                if lag > 0 and lag < win:
                    r = np.corrcoef(a_w[lag:], m_w[:-lag])[0, 1]
                elif lag < 0 and -lag < win:
                    r = np.corrcoef(a_w[:lag], m_w[-lag:])[0, 1]
                else:
                    r = np.corrcoef(a_w, m_w)[0, 1]
                if np.isfinite(r) and r > best_r:
                    best_r = r
                    best_l = lag

            window_corrs.append(best_r)
            window_lags.append(best_l)

        if not window_corrs:
            window_corrs = [global_corr]
            window_lags = [best_lag]

        # --- C. Skor Hesaplama ---
        avg_window_corr = float(np.mean(window_corrs))
        lag_jitter = float(np.std(window_lags)) if len(window_lags) > 1 else 0.0

        # Nihai senkron skoru: Global + Pencere ortalaması (ağırlıklı)
        sync_quality = (global_corr * 0.4) + (avg_window_corr * 0.6)
        sync_quality = float(np.clip(sync_quality, -1.0, 1.0))

        # --- D. Risk Puanı (0-100) ---
        # Yüksek senkron = Düşük risk (gerçek video)
        # Düşük/negatif senkron = Yüksek risk (deepfake)
        # NOT: Negatif korelasyon deepfake olmak zorunda değil — gürültü da olabilir.
        # Bu yüzden negatif korelasyonu 0 gibi ele alıyoruz (riskin tavanını sınırlıyoruz).
        sync_clamped = max(0.0, sync_quality)  # Negatif korelasyonu 0'a sabitle
        jitter_penalty = min(15.0, lag_jitter * 3.0)  # Jitter etkisini yumuşat

        # sync_clamped: 0 (kötü) -> 1 (iyi)
        # Risk: 0 (güvenli) -> 100 (riskli)
        base_risk = (1.0 - sync_clamped) * 65.0  # Max 65 — uç değerlere gitmesin
        risk_puani = float(np.clip(base_risk + jitter_penalty, 5.0, 80.0))

        return {
            "best_lag_frames": best_lag,
            "correlation_score": float(np.clip((sync_quality + 1) / 2, 0.0, 1.0)),  # 0-1 arası güven
            "lag_jitter": lag_jitter,
            "risk_score_calculated": risk_puani
        }

# ===========================================================================
# 5. BÖLÜM: ANA KONTROLCÜ
# ===========================================================================
class VeraDeep:
    """Tüm analiz alt sistemlerini birleştiren ve JSON raporu üreten ana kontrolcü sınıf."""
    def analyze(self, video_path: str) -> SyncReport:
        print("[SİSTEM] A/V Senkron Analizi Başlatılıyor...")

        # 1. Ses çıkar (ffmpeg öncelikli — MoviePy’den belirgin hızlı)
        audio_path = "temp_vera_audio.wav"
        if _wav_cikar_ffmpeg(video_path, audio_path, 16000):
            print("[BİLGİ] Ses ffmpeg ile WAV'a çevrildi (MoviePy'den hızlı).")
        else:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path, fps=16000, verbose=False, logger=None)
            video.close()

        preprocessor = AudioPreprocessor()
        audio_feats = preprocessor.extract(audio_path)

        flatness_score = getattr(preprocessor, "avg_flatness", 0.01)
        mfcc_var = getattr(preprocessor, "mfcc_variance", 50.0)
        zcr_std = getattr(preprocessor, "zcr_std", 0.05)

        # Normalize et ve birleştir
        # Flatness yüksekse kötü (robotik) — eşik: 0.08 (daha toleranslı)
        flatness_risk = min(25.0, (flatness_score / 0.08) * 10.0)
        # MFCC varyansı düşükse kötü (monoton) — eşik: 15 (daha toleranslı)
        mfcc_risk = min(20.0, max(0.0, (1.0 - mfcc_var / 15.0) * 20.0))
        # ZCR std yüksekse şüpheli — eşik: 0.08
        zcr_risk = min(15.0, (zcr_std / 0.08) * 8.0)

        acoustic_risk = flatness_risk + mfcc_risk + zcr_risk  # 0-60 arası

        # 2. Dudak hareketlerini işle
        frames = FacialLandmarkExtractor().process_video(video_path)

        # 3. Sinyalleri aynı zaman eksenine eşleştir (interpolasyon)
        mar_values = np.array([f.mar for f in frames])
        n_frames = len(frames)
        n_rms = len(audio_feats.rms_energy)

        audio_resampled = np.interp(
            np.linspace(0, n_rms - 1, n_frames),
            np.arange(n_rms),
            audio_feats.rms_energy
        )

        # 4. Senkronizasyon skoru
        sync_result = SyncAnalyzer().compute_sync_score(audio_resampled, mar_values)
        correlation_score = sync_result["correlation_score"]

        # 5. Yüz tespiti ve nihai karar
        face_ratio = sum(f.face_detected for f in frames) / max(len(frames), 1)
        risk_score_raw = sync_result.get("risk_score_calculated", 50.0) / 100.0
        lag_jitter = sync_result.get("lag_jitter", 0)

        if face_ratio < 0.20:
            scenario = "BELİRSİZ: Yüz yeterince tespit edilemedi"
            risk_score = (0.25 + acoustic_risk / 100.0) / 2
        else:
            # Senkron + Akustik kombinasyonu (%60 senkron, %40 akustik)
            combined_risk = (risk_score_raw * 0.60) + ((acoustic_risk / 70.0) * 0.40)
            combined_risk = float(np.clip(combined_risk, 0.05, 0.95))
            risk_score = combined_risk

            if combined_risk > 0.60:
                scenario = f"KRİTİK RİSK: Ses yapay/uyumsuz (Senkron={risk_score_raw:.2f}, Akustik={acoustic_risk:.1f}/70)"
            elif combined_risk > 0.40:
                scenario = f"ŞÜPHELİ: Kısmi ses anomalisi (Senkron={risk_score_raw:.2f}, Akustik={acoustic_risk:.1f}/70)"
            else:
                scenario = f"GÜVENLİ: Ses doğal ve uyumlu (Senkron={risk_score_raw:.2f}, Akustik={acoustic_risk:.1f}/70)"

        report = SyncReport(
            primary_speaker_confidence=round(correlation_score, 4),
            background_noise_level=audio_feats.noise_level,
            sync_lag_compensation=sync_result["best_lag_frames"],
            final_risk_score=round(float(risk_score), 4),
            detected_scenario=scenario,
            frame_level_anomalies=[f"Lag Jitter: {lag_jitter:.4f}", f"Yüz Tespit Oranı: {face_ratio:.2f}"]
        )

        rapor_sozlugu = {"VeraDeep_Sync_Report": asdict(report)}
        with open("senkron_analiz_raporu.json", "w", encoding="utf-8") as f:
            json.dump(rapor_sozlugu, f, indent=4, ensure_ascii=False)

        if Path(audio_path).exists():
            Path(audio_path).unlink()

        print(f"\n{'='*58}")
        print(f"  SES TEŞHİS : {scenario}")
        print(f"  SES SKORU  : %{risk_score * 100:.2f}")
        print(f"{'='*58}\n")

        return report


if __name__ == "__main__":
    import sys
    
    # Scriptin bulunduğu dizini al
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Argüman varsa onu kullan, yoksa test.mp4'ü dene
    hedef = sys.argv[1] if len(sys.argv) > 1 else "test.mp4"
    
    # AKILLI YOL ÇÖZÜCÜ: Önce CWD, sonra script dizini
    if os.path.exists(hedef):
        video_yolu = hedef
    else:
        alternatif = os.path.join(script_dir, hedef)
        if os.path.exists(alternatif):
            video_yolu = alternatif
        else:
            video_yolu = None

    if video_yolu:
        print(f"[SİSTEM] Video bulundu: {os.path.abspath(video_yolu)}")
        motor = VeraDeep()
        rapor = motor.analyze(video_yolu)
        
        print("\n" + "=" * 50)
        print("VERADEEP A/V SENKRONİZASYON RAPORU")
        print("=" * 50)
        print(f"Video        : {os.path.basename(video_yolu)}")
        print(f"Teşhis       : {rapor.detected_scenario}")
        print(f"Güven Skoru  : {rapor.primary_speaker_confidence:.4f}")
        print(f"Risk Skoru   : %{rapor.final_risk_score * 100:.2f}")
        print(f"Gürültü      : {rapor.background_noise_level}")
        print(f"Lag Telafisi : {rapor.sync_lag_compensation} kare")
        print("-" * 50)
        print("[SİSTEM] Rapor 'senkron_analiz_raporu.json' olarak diske kaydedildi.")
    else:
        print(f"\n[HATA] '{hedef}' dosyası bulunamadı!")
        print(f"[İPUCU] Aranan yerler:\n  1. {os.getcwd()}\n  2. {script_dir}")
        print("\nKullanım: python ses_motoru.py 'videonun_yolu.mp4'")