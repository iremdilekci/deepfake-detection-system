import os
import json
import numpy as np
import torch
from PIL import Image
from transformers import pipeline

class YapayZekaAnalizMotoru:
    """Hugging Face modelleri ile görsel deepfake tespiti yapan ve raporlayan sınıf."""

    def __init__(self, model_id="dima806/deepfake_vs_real_image_detection"):
        self.model_id = model_id
        # Sistemin ekran kartı (CUDA) kullanıp kullanamayacağını denetler
        self.cihaz = 0 if torch.cuda.is_available() else -1
        self._modeli_yukle()

    def _modeli_yukle(self):
        """Yapay zeka modelini internetten veya önbellekten donanıma taşır."""
        print(f"[SİSTEM] Yapay Zeka Modeli Belleğe Alınıyor: {self.model_id}")
        self.dedektif = pipeline("image-classification", model=self.model_id, device=self.cihaz)

    def _klasor_kontrolu(self, klasor_yolu):
        """Analiz edilecek görüntülerin bulunduğu klasörü doğrular."""
        if not os.path.isdir(klasor_yolu):
            print(f"[HATA] '{klasor_yolu}' klasörü bulunamadı.")
            return []
        dosyalar = [f for f in os.listdir(klasor_yolu) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        return dosyalar

    def kareleri_isle(self, klasor_yolu="VeraDeep_Kareler"):
        """Klasördeki tüm kareleri modele sokarak sahtelik skorlarını çıkarır."""
        dosyalar = self._klasor_kontrolu(klasor_yolu)
        if not dosyalar:
            return []

        print("-" * 50)
        print(f"[ANALİZ] Toplam {len(dosyalar)} kare işleniyor...")
        skor_listesi = []

        for dosya in dosyalar:
            tam_yol = os.path.join(klasor_yolu, dosya)
            try:
                img = Image.open(tam_yol).convert("RGB")
                tahminler = self.dedektif(img)
                
                # Modelin 'fake' veya 'LABEL_1' (Sahte) dediği değeri buluyoruz
                fake_skoru = 0.0
                for t in tahminler:
                    label = t['label'].lower()
                    if 'fake' in label or 'label_1' in label:
                        fake_skoru = t['score']
                        break
                
                skor_listesi.append(fake_skoru)
                
                # Terminalde görsel ilerleme takibi
                bar_uzunlugu = 20
                dolu_bar = int(fake_skoru * bar_uzunlugu)
                grafik = "X" * dolu_bar + "-" * (bar_uzunlugu - dolu_bar)
                print(f"|> {dosya[:15]:<15} |{grafik}| %{fake_skoru*100:.2f}")

            except Exception as e:
                print(f"[HATA] {dosya} işlenemedi: {e}")
                
        return skor_listesi

    def istatistik_ve_rapor_olustur(self, skor_listesi):
        """Elde edilen skorlardan nihai bir teşhis çıkarır ve JSON olarak kaydeder."""
        if not skor_listesi:
            return

        # Matematiksel Analiz
        ortalama_yuzde = float(np.mean(skor_listesi) * 100)
        maksimum_yuzde = float(np.max(skor_listesi) * 100)
        tutarlilik = float((1 - np.std(skor_listesi)) * 100)

        # Karar Mekanizması
        if ortalama_yuzde >= 75:
            teshis = "KRİTİK RİSK: KESİN DEEPFAKE"
            ozet = "Görüntüde yoğun yapay zeka manipülasyonu tespit edildi."
        elif ortalama_yuzde >= 50:
            teshis = "YÜKSEK RİSK: ŞÜPHELİ"
            ozet = "Belirgin tutarsızlıklar tespit edildi. Yapay zeka müdahalesi muhtemel."
        elif ortalama_yuzde >= 30:
            teshis = "DÜŞÜK RİSK: TEKNİK ANOMALİ"
            ozet = "Hafif düzensizlikler var (ışık/kalite kaynaklı olabilir)."
        else:
            teshis = "TEMİZ: DOĞAL İNSAN"
            ozet = "Görüntüde yapay zeka müdahalesine dair kanıt bulunamadı."

        # Backend ve Frontend iletişimi için veri paketi
        final_rapor = {
            "VeraDeep_Audit_Report": {
                "Analiz_Ozet": teshis,
                "Genel_Sahtelik_Olasiligi": f"%{ortalama_yuzde:.2f}",
                "En_Yuksek_Risk_Noktasi": f"%{maksimum_yuzde:.2f}",
                "Sistem_Tutarliligi": f"%{tutarlilik:.2f}",
                "Teknik_Aciklama": ozet,
                "Detaylar": {
                    "Incelenen_Kare_Sayisi": len(skor_listesi),
                    "Model_Mimarisi": self.model_id,
                    "Cihaz": "GPU-CUDA" if self.cihaz == 0 else "CPU"
                }
            }
        }

        with open("final_analiz_raporu.json", "w", encoding="utf-8") as f:
            json.dump(final_rapor, f, indent=4, ensure_ascii=False)

        # Özet JSON Çıktısı (Frontend'de hızlı göstermek için ideal)
        ozet_json = {
            "fake_olasiligi": f"%{ortalama_yuzde:.2f}",
            "teshis": teshis.split(":")[0],
            "esik_oneri": "0-30:Gercek, 30-60:Supheli, 60-100:Sahte"
        }

        with open("ozet_sonuc.json", "w", encoding="utf-8") as f:
            json.dump(ozet_json, f, indent=4, ensure_ascii=False)

        print("\n" + "=" * 50)
        print(f"FİNAL TEŞHİS: {teshis}")
        print(f"RİSK SKORU: %{ortalama_yuzde:.2f}")
        print(f"GÜVEN ANALİZİ: {ozet}")
        print("=" * 50 + "\n")
        print("[SİSTEM] JSON Raporları başarıyla kaydedildi.")

    def calistir(self, klasor_yolu="VeraDeep_Kareler"):
        """Tüm süreci uçtan uca çalıştıran ana metod."""
        skorlar = self.kareleri_isle(klasor_yolu)
        self.istatistik_ve_rapor_olustur(skorlar)

if __name__ == "__main__":
    motor = YapayZekaAnalizMotoru()
    motor.calistir()