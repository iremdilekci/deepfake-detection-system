from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
import os

# Scriptin bulunduğu dizin — video ve çıkış yolları buna göre çözülecek
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_VIDEO_EL = os.environ.get("VERADEEP_VIDEO_EL_KONTROL", "0").strip().lower() in ("1", "true", "yes")

# Varsayılan: kırpım videodaki gerçek piksel boyutunda, yeniden boyutlandırma YOK (interpolasyon yok = kalite kaybı yok).
_VIDEODAKI_COZUNURLUK = os.environ.get("VERADEEP_YUZ_VIDEODAKI_COZUNURLUK", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "hayir",
)

# Sabit kare kenarı (px) — sadece VERADEEP_YUZ_VIDEODAKI_COZUNURLUK=0 iken kullanılır (isteğe bağlı küçültme/büyütme).
_SABIT_KENAR_RAW = os.environ.get("VERADEEP_YUZ_SABIT_KENAR", "").strip()

# png = kayıpsız (önerilen); jpg = VERADEEP_JPEG_KALITE (varsayılan 100)
_YUZ_FORMAT = os.environ.get("VERADEEP_YUZ_FORMAT", "png").strip().lower()
if _YUZ_FORMAT not in ("png", "jpg", "jpeg"):
    _YUZ_FORMAT = "png"

_JPEG_KALITE = int(os.environ.get("VERADEEP_JPEG_KALITE", "100") or "100")
_JPEG_KALITE = max(90, min(_JPEG_KALITE, 100))


def _yuz_oval_indeksleri():
    oval = set()
    for a, b in mp.solutions.face_mesh.FACEMESH_FACE_OVAL:
        oval.add(a)
        oval.add(b)
    return oval


_FACE_OVAL_IDX = _yuz_oval_indeksleri()


def _yeniden_boyut_kare(bgr: np.ndarray, kenar: int) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h < 1 or w < 1:
        return bgr
    if h >= kenar and w >= kenar:
        return cv2.resize(bgr, (kenar, kenar), interpolation=cv2.INTER_AREA)
    return cv2.resize(bgr, (kenar, kenar), interpolation=cv2.INTER_LANCZOS4)


class VideoYuzKesici:
    """Videodan yüz bölgesini kırpar; varsayılan olarak videonun çözünürlüğünde kayıpsız (PNG) saklar."""

    def __init__(self, cikis_klasoru="VeraDeep_Kareler"):
        if not os.path.isabs(cikis_klasoru):
            cikis_klasoru = os.path.join(_SCRIPT_DIR, cikis_klasoru)
        self.cikis_klasoru = os.path.abspath(cikis_klasoru)
        self.videodaki_cozunurluk = _VIDEODAKI_COZUNURLUK
        self.sabit_kenar: int | None = None
        if _SABIT_KENAR_RAW.isdigit():
            k = int(_SABIT_KENAR_RAW)
            if k >= 64:
                self.sabit_kenar = min(k, 4096)
        self.kayit_uzantisi = ".png" if _YUZ_FORMAT == "png" else ".jpg"
        self.jpeg_kalite = _JPEG_KALITE
        self.blur_esigi = 15.0

        self._klasoru_hazirla()
        self._modelleri_yukle()

    def _klasoru_hazirla(self):
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
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )
        self.mp_hands = mp.solutions.hands
        self.hands = (
            self.mp_hands.Hands(
                static_image_mode=True,
                max_num_hands=2,
                min_detection_confidence=0.5,
            )
            if _VIDEO_EL
            else None
        )

    def _guvenli_kaydet(self, dosya_yolu: str, resim: np.ndarray) -> bool:
        try:
            if dosya_yolu.lower().endswith(".png"):
                params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
                is_success, buf = cv2.imencode(".png", resim, params)
            else:
                params = [
                    int(cv2.IMWRITE_JPEG_QUALITY),
                    self.jpeg_kalite,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE),
                    1,
                ]
                is_success, buf = cv2.imencode(".jpg", resim, params)
            if is_success:
                buf.tofile(dosya_yolu)
                return True
            return False
        except Exception as e:
            print(f"[HATA] Kayıt yapılamadı: {e}")
            return False

    def _el_yuzu_kapatmis_mi(self, yuz_kordinatlari, el_sonuclari, img_h, img_w):
        if el_sonuclari is None or not el_sonuclari.multi_hand_landmarks:
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

    def _yuz_kare_kirp(self, frame: np.ndarray, lms, h: int, w: int) -> np.ndarray | None:
        """
        Yüz ovali + pay: videonun piksel ızgarasından doğrudan kırpım (ek ölçekleme yok).
        Dikdörtgen kutu — yüzü kesmeden maksimum çözünürlük.
        """
        raw_m = os.environ.get("VERADEEP_YUZ_MARGIN", "0.45").strip().replace(",", ".")
        try:
            margin = float(raw_m)
        except ValueError:
            margin = 0.20
        margin = 0.20 # Daha dar çerçeve ile yüz detaylarına odaklanma

        xs = [int(lms[i].x * w) for i in _FACE_OVAL_IDX]
        ys = [int(lms[i].y * h) for i in _FACE_OVAL_IDX]
        if not xs:
            return None

        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        fw, fh = xmax - xmin, ymax - ymin
        if fw < 8 or fh < 8:
            return None

        pad_x = int(fw * margin)
        pad_y = int(fh * margin)
        x1 = max(0, xmin - pad_x)
        y1 = max(0, ymin - pad_y)
        x2 = min(w, xmax + pad_x)
        y2 = min(h, ymax + pad_y)

        if x2 <= x1 or y2 <= y1:
            return None

        kesit = frame[y1:y2, x1:x2]
        if kesit.size == 0 or kesit.shape[0] < 8 or kesit.shape[1] < 8:
            return None
        return kesit

    def videoyu_isle(self, video_yolu="test.mp4", hedeflenen_fps=None):
        if hedeflenen_fps is None:
            raw = os.environ.get("VERADEEP_VIDEO_HEDEF_FPS", "2.5").strip()
            try:
                hedeflenen_fps = float(raw.replace(",", "."))
            except ValueError:
                hedeflenen_fps = 2.5
            hedeflenen_fps = max(0.25, min(hedeflenen_fps, 30.0))

        if not os.path.isabs(video_yolu) and not os.path.exists(video_yolu):
            alternatif = os.path.join(_SCRIPT_DIR, video_yolu)
            if os.path.exists(alternatif):
                video_yolu = alternatif

        print(f"[BİLGİ] Analiz başlatılıyor: {video_yolu}")
        if self.videodaki_cozunurluk and self.sabit_kenar is None:
            print(
                f"[BİLGİ] Yüz kırpımı: videodaki çözünürlükte (yeniden boyutlandırma yok), "
                f"format={_YUZ_FORMAT.upper()} (VERADEEP_YUZ_FORMAT)"
            )
        else:
            kenar = self.sabit_kenar or 720
            print(
                f"[BİLGİ] Yüz kırpımı: sabit {kenar}x{kenar} px (VERADEEP_YUZ_SABIT_KENAR / "
                f"VERADEEP_YUZ_VIDEODAKI_COZUNURLUK=0), format={_YUZ_FORMAT.upper()}"
            )

        cap = cv2.VideoCapture(video_yolu)
        if not cap.isOpened():
            print(f"[HATA] Video açılamadı: {video_yolu}")
            return

        orijinal_fps = cap.get(cv2.CAP_PROP_FPS)
        toplam_kare = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if orijinal_fps <= 0:
            orijinal_fps = 30.0

        atlama_kare_sayisi = int(orijinal_fps / hedeflenen_fps)
        if atlama_kare_sayisi < 1:
            atlama_kare_sayisi = 1

        print(f"[BİLGİ] Video: {toplam_kare} kare @ {orijinal_fps:.1f} FPS, çerçeve ~{vw}x{vh}")
        print(f"[BİLGİ] Her {atlama_kare_sayisi} karede bir (~{hedeflenen_fps} FPS)")

        kare_idx = 0
        kayit_sayaci = 0
        blur_reddedilen = 0
        yuz_yok = 0
        el_reddedilen = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if kare_idx % atlama_kare_sayisi == 0:
                h, w, _ = frame.shape

                gri = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur_skoru = cv2.Laplacian(gri, cv2.CV_64F).var()
                if blur_skoru < self.blur_esigi:
                    blur_reddedilen += 1
                    kare_idx += 1
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                yuz_sonucu = self.face_mesh.process(rgb)
                el_sonucu = self.hands.process(rgb) if self.hands else None

                if not yuz_sonucu.multi_face_landmarks:
                    yuz_yok += 1
                    kare_idx += 1
                    continue

                lms = yuz_sonucu.multi_face_landmarks[0].landmark

                if self.hands and self._el_yuzu_kapatmis_mi(lms, el_sonucu, h, w):
                    el_reddedilen += 1
                    kare_idx += 1
                    continue

                yuz_kesit = self._yuz_kare_kirp(frame, lms, h, w)
                if yuz_kesit is None:
                    yuz_yok += 1
                    kare_idx += 1
                    continue

                if self.videodaki_cozunurluk and self.sabit_kenar is None:
                    cikti = yuz_kesit
                else:
                    kenar = self.sabit_kenar or 720
                    cikti = _yeniden_boyut_kare(yuz_kesit, kenar)

                dosya_adi = f"yuz_{kayit_sayaci:04d}{self.kayit_uzantisi}"
                dosya_yolu = os.path.join(self.cikis_klasoru, dosya_adi)
                if self._guvenli_kaydet(dosya_yolu, cikti):
                    kayit_sayaci += 1

            kare_idx += 1

        cap.release()
        print(f"[SİSTEM] İşlem tamamlandı. Toplam {kayit_sayaci} yüz karesi kaydedildi.")
        print(f"[STAT]  Blur reddi: {blur_reddedilen} | Yüz yok: {yuz_yok} | El reddi: {el_reddedilen}")
        if kayit_sayaci == 0:
            print("[UYARI] Hiç kare kaydedilemedi! Video'da yüz tespit edilememiş olabilir.")


if __name__ == "__main__":
    islem_motoru = VideoYuzKesici(cikis_klasoru="VeraDeep_Kareler")
    islem_motoru.videoyu_isle("test.mp4")
