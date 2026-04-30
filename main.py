import os
import json
import warnings
import cv2
import torch
import librosa
import numpy as np
import mediapipe as mp
from PIL import Image
from transformers import pipeline
from scipy.signal import butter, sosfilt, correlate
from moviepy.editor import VideoFileClip

warnings.filterwarnings("ignore")

# ===========================================================================
# 1. MOTOR: OTONOM YUZ KESICI (VERI HAZIRLIGI)
# ===========================================================================
class VideoYuzKesici:
    """
    [SUNUM NOTU]: Bu modul, ham videodaki yuzleri bulaniklik testinden gecirerek
    yapay zeka modelinin anlayacagi 224x224 boyutunda standart karelere cevirir.
    """
    def __init__(self, cikis_klasoru="VeraDeep_Kareler"):
        self.cikis_klasoru = os.path.abspath(cikis_klasoru)
        self.hedef_boyut = (224, 224)
        self.blur_esigi = 15.0  
        
        # Klasor temizligi
        if os.path.exists(self.cikis_klasoru):
            for dosya in os.listdir(self.cikis_klasoru):
                dosya_yolu = os.path.join(self.cikis_klasoru, dosya)
                if os.path.isfile(dosya_yolu): os.unlink(dosya_yolu)
        else:
            os.makedirs(self.cikis_klasoru)

        self.face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

    def _guvenli_kaydet(self, dosya_yolu, resim):
        """Turkce karakter iceren yollarda (Masaustu vb.) cokmeyi engeller."""
        is_success, im_buf_arr = cv2.imencode(".jpg", resim)
        if is_success:
            im_buf_arr.tofile(dosya_yolu)

    def videoyu_isle(self, video_yolu="test.mp4"):
        cap = cv2.VideoCapture(video_yolu)
        kare_idx, kayit_sayaci = 0, 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            if kare_idx % 2 == 0:
                h, w, _ = frame.shape
                gri = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur_skoru = cv2.Laplacian(gri, cv2.CV_64F).var()
                
                if blur_skoru > self.blur_esigi:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    yuz_sonucu = self.face_mesh.process(rgb)
                    
                    if yuz_sonucu.multi_face_landmarks:
                        lms = yuz_sonucu.multi_face_landmarks[0].landmark
                        x_pts = [int(lm.x * w) for lm in lms]
                        y_pts = [int(lm.y * h) for lm in lms]
                        yuz_w, yuz_h = max(x_pts) - min(x_pts), max(y_pts) - min(y_pts)
                        
                        y1 = max(0, int(min(y_pts) - (yuz_h * 0.35)))
                        y2 = min(h, int(max(y_pts) + (yuz_h * 0.20)))
                        x1 = max(0, int(min(x_pts) - (yuz_w * 0.25)))
                        x2 = min(w, int(max(x_pts) + (yuz_w * 0.25)))

                        yuz_kesit = frame[y1:y2, x1:x2]
                        if yuz_kesit.size > 0:
                            yuz_kesit = cv2.resize(yuz_kesit, self.hedef_boyut)
                            dosya_adi = os.path.join(self.cikis_klasoru, f"yuz_{kayit_sayaci:04d}.jpg")
                            self._guvenli_kaydet(dosya_adi, yuz_kesit)
                            kayit_sayaci += 1
            kare_idx += 1
        cap.release()

# ===========================================================================
# 2. MOTOR: GORSEL YAPAY ZEKA AGI (INFERENCE)
# ===========================================================================
class YapayZekaAnalizMotoru:
    """
    [SUNUM NOTU]: Bu modul, temizlenen yuzleri onceden egitilmis bir Derin Ogrenme 
    agina sokarak piksellerdeki manipulasyonlari istatistiksel olarak arar.
    """
    def __init__(self, model_id="dima806/deepfake_vs_real_image_detection"):
        self.cihaz = 0 if torch.cuda.is_available() else -1
        self.dedektif = pipeline("image-classification", model=model_id, device=self.cihaz)

    def calistir(self, klasor_yolu="VeraDeep_Kareler"):
        dosyalar = [f for f in os.listdir(klasor_yolu) if f.lower().endswith('.jpg')]
        skor_listesi = []

        for dosya in dosyalar:
            try:
                img = Image.open(os.path.join(klasor_yolu, dosya)).convert("RGB")
                tahminler = self.dedektif(img)
                for t in tahminler:
                    if 'fake' in t['label'].lower() or 'label_1' in t['label'].lower():
                        skor_listesi.append(t['score'])
                        break
            except: continue

        if skor_listesi:
            ortalama = float(np.mean(skor_listesi) * 100)
            rapor = {"VeraDeep_Audit_Report": {"Genel_Sahtelik_Olasiligi": f"%{ortalama:.2f}"}}
            with open("final_analiz_raporu.json", "w", encoding="utf-8") as f:
                json.dump(rapor, f, indent=4)

# ===========================================================================
# 3. MOTOR: SES VE DUDAK SENKRONIZASYONU (LIP-SYNC)
# ===========================================================================
class SenkronMotoru:
    """
    [SUNUM NOTU]: Bu modul, insan anatomisi geregi sesin siddeti (RMS) ile 
    dudak acikligi (MAR) arasindaki matematiksel baglantiyi (Korelasyon) inceler.
    """
    def analyze(self, video_path: str):
        audio_path = "temp_vera_audio.wav"
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path, fps=16000, verbose=False, logger=None)
            video.close()
        except Exception:
            # Videoda ses yoksa guvenli cikis yap
            rapor_sozlugu = {"VeraDeep_Sync_Report": {"final_risk_score": 0.0}}
            with open("senkron_analiz_raporu.json", "w", encoding="utf-8") as f:
                json.dump(rapor_sozlugu, f, indent=4)
            return

        raw, sr = librosa.load(audio_path, sr=16000, mono=True)
        rms = librosa.feature.rms(y=raw, hop_length=512)[0]
        
        face_mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1)
        cap = cv2.VideoCapture(video_path)
        mar_values = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            result = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if result.multi_face_landmarks:
                lms = result.multi_face_landmarks[0].landmark
                ust_y, alt_y = lms[13].y, lms[14].y
                mar_values.append(abs(alt_y - ust_y))
            else:
                mar_values.append(0.0)
        cap.release()

        length = min(len(rms), len(mar_values))
        a, m = rms[:length], np.array(mar_values[:length])
        
        a_norm = (a - a.mean()) / (a.std() + 1e-6)
        m_norm = (m - m.mean()) / (m.std() + 1e-6)
        
        corr = correlate(a_norm, m_norm, mode="full")
        max_corr = np.clip(np.max(corr) / (len(a_norm) + 1e-6), 0.0, 1.0)
        risk_skoru = 1.0 - max_corr

        rapor_sozlugu = {"VeraDeep_Sync_Report": {"final_risk_score": float(risk_skoru)}}
        with open("senkron_analiz_raporu.json", "w", encoding="utf-8") as f:
            json.dump(rapor_sozlugu, f, indent=4)
            
        if os.path.exists(audio_path): os.unlink(audio_path)

# ===========================================================================
# 4. ORKESTRA SEFI (API / MAIN KONTROLCU)
# ===========================================================================
def sistemi_baslat(video_adi="test.mp4"):
    """
    [SUNUM NOTU]: Tum motorlari sirayla cagirir, sonuclari toplar ve
    sistemin nihai kararini hem ekrana basar hem de tek bir JSON dosyasina yazar.
    """
    print("\n[SISTEM] VeraDeep Motorlari Calistiriliyor...")

    print("-> Adim 1: Video Kesici aktif...")
    VideoYuzKesici().videoyu_isle(video_adi)

    print("-> Adim 2: Gorsel Yapay Zeka aktif...")
    YapayZekaAnalizMotoru().calistir("VeraDeep_Kareler")

    print("-> Adim 3: Ses/Dudak Senkron Analizi aktif...")
    SenkronMotoru().analyze(video_adi)

    print("\n[SISTEM] Analizler Birlestiriliyor...")
    try:
        with open("final_analiz_raporu.json", "r", encoding="utf-8") as f:
            gorsel_skor = float(json.load(f)["VeraDeep_Audit_Report"]["Genel_Sahtelik_Olasiligi"].replace("%", ""))
        with open("senkron_analiz_raporu.json", "r", encoding="utf-8") as f:
            senkron_skor = float(json.load(f)["VeraDeep_Sync_Report"]["final_risk_score"]) * 100

        # %70 Goruntu, %30 Ses Agirligi
        final_skor = (gorsel_skor * 0.70) + (senkron_skor * 0.30)
        karar = "KESIN DEEPFAKE" if final_skor > 65 else "SUPHELI" if final_skor > 40 else "DOGAL INSAN"

        # --- TEK VE NIHAİ JSON ÇIKTISI ---
        nihai_rapor = {
            "VeraDeep_Nihai_Rapor": {
                "Gorsel_Risk_Skoru": round(gorsel_skor, 2),
                "Senkron_Risk_Skoru": round(senkron_skor, 2),
                "Final_Deepfake_Ihtimali": round(final_skor, 2),
                "Sistem_Karari": karar
            }
        }
        
        with open("veradeep_nihai_rapor.json", "w", encoding="utf-8") as f:
            json.dump(nihai_rapor, f, indent=4, ensure_ascii=False)

        print("\n" + "="*50)
        print("VERADEEP UCTAN UCA ANALIZ SONUCU")
        print("="*50)
        print(f"Gorsel Hata Skoru : %{gorsel_skor:.2f}")
        print(f"Senkron Hata Skoru: %{senkron_skor:.2f}")
        print("-" * 50)
        print(f"FINAL RİSK SKORU  : %{final_skor:.2f}")
        print(f"SISTEM KARARI     : {karar}")
        print("="*50 + "\n")
        print("[BILGI] Rapor 'veradeep_nihai_rapor.json' olarak kaydedildi.")

    except Exception as e:
        print(f"[HATA] Raporlar okunamadi: {e}")

if __name__ == "__main__":
    import sys
    hedef = sys.argv[1] if len(sys.argv) > 1 else "test.mp4"
    if os.path.exists(hedef):
        sistemi_baslat(hedef)
    else:
        print(f"[HATA] {hedef} dosyasi bulunamadi!")