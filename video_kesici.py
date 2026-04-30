import cv2
import mediapipe as mp
import numpy as np
import os

class VideoYuzKesici:
    """Videolardan standartlaştırılmış yüz kareleri çıkaran ana sınıf."""
    
    def __init__(self, cikis_klasoru="VeraDeep_Kareler"):
        self.cikis_klasoru = os.path.abspath(cikis_klasoru)
        self.hedef_boyut = (224, 224)
        self.blur_esigi = 15.0  
        
        self._klasoru_hazirla()
        self._modelleri_yukle()

    def _klasoru_hazirla(self):
        """Eski verileri temizler veya yeni klasör oluşturur."""
        if os.path.exists(self.cikis_klasoru):
            print(f"[SİSTEM] Eski veriler temizleniyor: {self.cikis_klasoru}")
            for dosya in os.listdir(self.cikis_klasoru):
                dosya_yolu = os.path.join(self.cikis_klasoru, dosya)
                try:
                    if os.path.isfile(dosya_yolu):
                        os.unlink(dosya_yolu)
                except Exception as e:
                    print(f"[HATA] Dosya silinemedi: {dosya_yolu} - {e}")
        else:
            os.makedirs(self.cikis_klasoru)
            print(f"[SİSTEM] Yeni klasör oluşturuldu: {self.cikis_klasoru}")

    def _modelleri_yukle(self):
        """MediaPipe yüz ve el tespit modellerini başlatır."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.6
        )
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5
        )

    def _guvenli_kaydet(self, dosya_yolu, resim):
        """Türkçe karakter içeren işletim sistemi yollarında hatasız kayıt yapar."""
        try:
            is_success, im_buf_arr = cv2.imencode(".jpg", resim)
            if is_success:
                im_buf_arr.tofile(dosya_yolu)
                return True
            return False
        except Exception as e:
            print(f"[HATA] Kayıt yapılamadı: {e}")
            return False

    def _el_yuzu_kapatmis_mi(self, yuz_kordinatlari, el_sonuclari, img_h, img_w):
        """Elin, yüz bölgesine belirlenen güvenlik payı (margin) kadar yaklaşıp yaklaşmadığını kontrol eder."""
        if not el_sonuclari.multi_hand_landmarks:
            return False
            
        yuz_x = [int(lm.x * img_w) for lm in yuz_kordinatlari]
        yuz_y = [int(lm.y * img_h) for lm in yuz_kordinatlari]
        
        kalkan_x_min, kalkan_x_max = min(yuz_x) - 40, max(yuz_x) + 40
        kalkan_y_min, kalkan_y_max = min(yuz_y) - 40, max(yuz_y) + 40
        
        for el_lms in el_sonuclari.multi_hand_landmarks:
            for nokta in el_lms.landmark:
                el_x, el_y = int(nokta.x * img_w), int(nokta.y * img_h)
                if (kalkan_x_min < el_x < kalkan_x_max) and (kalkan_y_min < el_y < kalkan_y_max):
                    return True
        return False

    def videoyu_isle(self, video_yolu="test.mp4"):
        """Videoyu kare kare okuyup ön işleme adımlarını uygular."""
        print(f"[BİLGİ] Analiz başlatılıyor: {video_yolu}")
        cap = cv2.VideoCapture(video_yolu)
        atlama_kare_sayisi = 2 
        kare_idx = 0
        kayit_sayaci = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: 
                break

            # Belirlenen aralıklarla (FPS düşürerek) analiz yap
            if kare_idx % atlama_kare_sayisi == 0:
                h, w, _ = frame.shape
                
                # 1. Blur (Bulanıklık) Kontrolü
                gri = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur_skoru = cv2.Laplacian(gri, cv2.CV_64F).var()
                if blur_skoru < self.blur_esigi:
                    kare_idx += 1
                    continue

                # 2. Yapay Zeka Çıkarımı
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yuz_sonucu = self.face_mesh.process(rgb)
                el_sonucu = self.hands.process(rgb)

                if yuz_sonucu.multi_face_landmarks:
                    lms = yuz_sonucu.multi_face_landmarks[0].landmark
                    
                    # 3. Güvenlik İhlali (El) Kontrolü
                    if self._el_yuzu_kapatmis_mi(lms, el_sonucu, h, w):
                        print(f"[{kare_idx}] Reddedildi: Yüz üzerinde el tespit edildi.")
                        kare_idx += 1
                        continue

                    # 4. Dinamik Kırpma (Crop) İşlemi
                    x_pts = [int(lm.x * w) for lm in lms]
                    y_pts = [int(lm.y * h) for lm in lms]
                    yuz_w, yuz_h = max(x_pts) - min(x_pts), max(y_pts) - min(y_pts)
                    
                    y1 = max(0, int(min(y_pts) - (yuz_h * 0.35)))
                    y2 = min(h, int(max(y_pts) + (yuz_h * 0.20)))
                    x1 = max(0, int(min(x_pts) - (yuz_w * 0.25)))
                    x2 = min(w, int(max(x_pts) + (yuz_w * 0.25)))

                    yuz_kesit = frame[y1:y2, x1:x2]
                    
                    # 5. Boyutlandırma ve Kayıt
                    if yuz_kesit.size > 0:
                        yuz_kesit = cv2.resize(yuz_kesit, self.hedef_boyut)
                        dosya_adi = f"yuz_{kayit_sayaci:04d}.jpg"
                        dosya_yolu = os.path.join(self.cikis_klasoru, dosya_adi)
                        
                        if self._guvenli_kaydet(dosya_yolu, yuz_kesit):
                            print(f"[{kare_idx}] Başarılı: {dosya_adi} kaydedildi.")
                            kayit_sayaci += 1

            kare_idx += 1

        cap.release()
        print(f"[SİSTEM] İşlem tamamlandı. Toplam {kayit_sayaci} kaliteli veri üretildi.")

if __name__ == "__main__":
    islem_motoru = VideoYuzKesici(cikis_klasoru="VeraDeep_Kareler")
    islem_motoru.videoyu_isle("test.mp4")