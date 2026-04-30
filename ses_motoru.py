import json
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import cv2
import librosa
import mediapipe as mp
import numpy as np
from scipy.signal import butter, sosfilt, correlate
from moviepy.editor import VideoFileClip

warnings.filterwarnings("ignore")

# ===========================================================================
# 1. BÖLÜM: VERİ YAPILARI (OUTPUT FORMATLARI)
# ===========================================================================
@dataclass
class FrameFeatures:
    frame_index: int
    timestamp_sec: float
    mar: float                  # Dudak Açıklık Oranı (Mouth Aspect Ratio)
    mar_delta: float            # Dudak hareket hızı
    face_detected: bool

@dataclass
class AudioFeatures:
    rms_energy: np.ndarray      # Sesin şiddeti/enerjisi
    speech_mask: np.ndarray     # Konuşma anlarını belirten maske (1/0)
    sample_rate: int
    noise_level: str            # Arka plan gürültü seviyesi

@dataclass
class SyncReport:
    primary_speaker_confidence: float   # Senkronizasyon güven skoru (0-1)
    background_noise_level: str         # Gürültü durumu
    sync_lag_compensation: int          # Sinyaller arası milisaniyelik kayma
    final_risk_score: float             # Nihai Deepfake riski (0-1)
    detected_scenario: str              # Sistemin koyduğu teşhis (A/B/C vb.)
    frame_level_anomalies: list[dict]   # Hatalı/Uyumsuz tespit edilen kareler

# ===========================================================================
# 2. BÖLÜM: SES SİNYALİ İŞLEME MODÜLÜ
# ===========================================================================
class AudioPreprocessor:
    """Sesi frekanslarına ayırıp insan sesi enerjisini (RMS) hesaplar."""
    def __init__(self, sample_rate=16000):
        self.sr = sample_rate

    def extract(self, audio_path: str) -> AudioFeatures:
        raw, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        # İnsan sesini (80Hz - 3400Hz) filtrele
        nyq = self.sr / 2.0
        sos = butter(5, [80 / nyq, 3400 / nyq], btype="band", output="sos")
        filtered = sosfilt(sos, raw)
        
        rms = librosa.feature.rms(y=filtered, hop_length=512)[0]
        mask = (rms > (np.median(rms) + 0.15 * np.std(rms))).astype(int)
        
        # Gürültü seviyesi tespiti
        ratio = (np.sqrt(np.mean(filtered ** 2)) + 1e-9) / (np.sqrt(np.mean(raw ** 2)) + 1e-9)
        noise_level = "low" if ratio > 0.75 else ("medium" if ratio > 0.40 else "high")

        return AudioFeatures(rms_energy=rms, speech_mask=mask, sample_rate=sr, noise_level=noise_level)

# ===========================================================================
# 3. BÖLÜM: GÖRÜNTÜ VE DUDAK (MAR) İŞLEME MODÜLÜ
# ===========================================================================
class FacialLandmarkExtractor:
    """Videodaki dudak hareketlerini (MAR) kare kare sayısallaştırır."""
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False, max_num_faces=1, refine_landmarks=True
        )

    def process_video(self, video_path: str) -> list[FrameFeatures]:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        features, prev_mar, frame_idx = [], 0.0, 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.face_mesh.process(rgb)

            if result.multi_face_landmarks:
                lms = result.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]
                
                # Alt ve üst dudak arası mesafenin hesaplanması (Basitleştirilmiş Matematik)
                upper = np.mean([[lms[i].x * w, lms[i].y * h] for i in [13, 312, 311, 310, 415, 308]], axis=0)
                lower = np.mean([[lms[i].x * w, lms[i].y * h] for i in [14, 317, 402, 318, 324, 78]], axis=0)
                mar = float(np.linalg.norm(lower - upper) / (np.linalg.norm([lms[308].x * w - lms[78].x * w, lms[308].y * h - lms[78].y * h]) + 1e-6))
                
                features.append(FrameFeatures(frame_idx, frame_idx / fps, mar, abs(mar - prev_mar), True))
                prev_mar = mar
            else:
                features.append(FrameFeatures(frame_idx, frame_idx / fps, 0.0, 0.0, False))
            frame_idx += 1

        cap.release()
        return features

# ===========================================================================
# 4. BÖLÜM: ÇAPRAZ KORELASYON (SENKRONİZASYON) MODÜLÜ
# ===========================================================================
class SyncAnalyzer:
    """Ses enerjisi ile dudak hareketini matematiksel olarak üst üste bindirir."""
    def compute_sync_score(self, audio_rms: np.ndarray, mar_values: np.ndarray) -> dict:
        length = min(len(audio_rms), len(mar_values))
        a, m = audio_rms[:length], mar_values[:length]
        
        # Sinyalleri normalize et
        a_norm = (a - a.mean()) / a.std() if a.std() > 1e-6 else a - a.mean()
        m_norm = (m - m.mean()) / m.std() if m.std() > 1e-6 else m - m.mean()

        # Çapraz Korelasyon (Zaman Kaydırmalı Benzerlik)
        corr = correlate(a_norm, m_norm, mode="full")
        lags = np.arange(-len(m_norm) + 1, len(a_norm))
        
        # Sadece +/- 15 karelik mantıklı gecikmelere bak
        corr[np.abs(lags) > 15] = -np.inf
        best_lag_idx = int(np.argmax(corr))
        
        score = float(np.clip(corr[best_lag_idx] / len(a_norm), 0.0, 1.0))
        return {"best_lag_frames": int(lags[best_lag_idx]), "correlation_score": score}

# ===========================================================================
# 5. BÖLÜM: KARAR MOTORU VE UÇTAN UCA ÇALIŞTIRMA
# ===========================================================================
class VeraDeep:
    """Tüm analiz alt sistemlerini birleştiren ve JSON raporu üreten ana kontrolcü sınıf."""
    def analyze(self, video_path: str) -> SyncReport:
        print("[SİSTEM] A/V Senkron Analizi Başlatılıyor...")
        
        # 1. Sesi Çıkar ve İşle
        audio_path = "temp_vera_audio.wav"
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, fps=16000, verbose=False, logger=None)
        video.close()
        
        audio_feats = AudioPreprocessor().extract(audio_path)
        
        # 2. Görüntüyü İşle (Dudak Hareketleri)
        frames = FacialLandmarkExtractor().process_video(video_path)
        
        # 3. Sinyalleri Eşleştir
        mar_values = np.array([f.mar for f in frames])
        audio_resampled = np.interp(np.linspace(0, len(audio_feats.rms_energy)-1, len(frames)), np.arange(len(audio_feats.rms_energy)), audio_feats.rms_energy)
        
        sync_result = SyncAnalyzer().compute_sync_score(audio_resampled, mar_values)
        correlation_score = sync_result["correlation_score"]

        # 4. Basit Senaryo Mantığı ve Karar
        face_ratio = sum(f.face_detected for f in frames) / max(len(frames), 1)
        
        if face_ratio > 0.5 and correlation_score < 0.30:
            scenario = "RİSKLİ: Dudak hareketli ama sesle uyumsuz (Deepfake Şüphesi)"
        elif face_ratio < 0.15:
            scenario = "DÜŞÜK RİSK: Yüz tespit edilemedi (Dış Ses / Narrator)"
        else:
            scenario = "GÜVENLİ: Dudak ve ses senkronizasyonu doğal."

        # Rapor Nesnesini Oluştur
        report = SyncReport(
            primary_speaker_confidence=round(correlation_score, 4),
            background_noise_level=audio_feats.noise_level,
            sync_lag_compensation=sync_result["best_lag_frames"],
            final_risk_score=round(1.0 - correlation_score, 4),
            detected_scenario=scenario,
            frame_level_anomalies=[]
        )

        # 5. JSON OLARAK DİSKE KAYDETME
        rapor_sozlugu = {"VeraDeep_Sync_Report": asdict(report)}
        with open("senkron_analiz_raporu.json", "w", encoding="utf-8") as f:
            json.dump(rapor_sozlugu, f, indent=4, ensure_ascii=False)

        # Geçici ses dosyasını sil
        if Path(audio_path).exists(): Path(audio_path).unlink()

        return report

if __name__ == "__main__":
    motor = VeraDeep()
    rapor = motor.analyze("test.mp4")
    
    print("\n" + "=" * 50)
    print("VERADEEP A/V SENKRONİZASYON RAPORU")
    print("=" * 50)
    print(f"Teşhis: {rapor.detected_scenario}")
    print(f"Güven Skoru: {rapor.primary_speaker_confidence}")
    print(f"Risk Skoru: {rapor.final_risk_score}")
    print("-" * 50)
    print("[SİSTEM] Rapor 'senkron_analiz_raporu.json' olarak diske kaydedildi.")