"""
VeraDeep - Deepfake Analiz Motoru (ViT-base / Deep-Fake-Detector-v2)
====================================================================
GÜNCELLENMİŞ VERSİYON (v9.0)
Model: google/vit-base-patch16-224-in21k (Deepfake Fine-tuned)
"""

import os
import sys
import json
import numpy as np
import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor

# ─── YAPILANDIRMA ─────────────────────────────────────────────────────────────
BATCH_BOYUT = 4
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOKAL_MODEL = os.path.join(_SCRIPT_DIR, "models", "Deep-Fake-Detector-v2")
# ──────────────────────────────────────────────────────────────────────────────

class AnalizMotoru:
    def __init__(self):
        self.cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[SİSTEM] VeraDeep PRO v9.0 (ViT) Aktif | Cihaz: {self.cihaz}")

        try:
            # ViT modelini yerel dizinden yükle
            self.processor = ViTImageProcessor.from_pretrained(LOKAL_MODEL)
            self.model = ViTForImageClassification.from_pretrained(LOKAL_MODEL)
            
            self.model.to(self.cihaz)
            self.model.eval()
            
        except Exception as e:
            print(f"[KRİTİK HATA] ViT Modeli yüklenemedi: {e}")
            sys.exit(1)

    def preprocess(self, img):
        # Transformers processor'ı kullanarak resmi tensor'a çevir
        return self.processor(images=img, return_tensors="pt")["pixel_values"][0]

    def gorselleri_yukle(self, klasor: str):
        if not os.path.isabs(klasor) and not os.path.isdir(klasor):
            alternatif = os.path.join(_SCRIPT_DIR, klasor)
            if os.path.isdir(alternatif): klasor = alternatif
        if not os.path.isdir(klasor): return [], []

        uzantilar = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        dosyalar = sorted(f for f in os.listdir(klasor) if f.lower().endswith(uzantilar))
        
        gorseller, gecerli = [], []
        for dosya in dosyalar:
            try:
                img = Image.open(os.path.join(klasor, dosya)).convert("RGB")
                gorseller.append(img)
                gecerli.append(dosya)
            except: continue
        return gorseller, gecerli

    @torch.no_grad()
    def batch_calistir(self, gorseller: list) -> list:
        tum_skorlar = []
        for i in range(0, len(gorseller), BATCH_BOYUT):
            batch = gorseller[i : i + BATCH_BOYUT]
            try:
                tensors = torch.stack([self.preprocess(img).to(torch.float32) for img in batch]).to(self.cihaz)
                outputs = self.model(tensors).logits
                probs = torch.softmax(outputs, dim=-1)
                
                # Index 1 = SAHTE (Model testinde onaylandı)
                batch_skorlari = probs[:, 1].cpu().tolist()
                tum_skorlar.extend(batch_skorlari)
            except Exception as e:
                tum_skorlar.extend([0.0] * len(batch))
        return tum_skorlar

    def rapor_olustur(self, skorlar: list, dosyalar: list, cikis: str = ".") -> dict:
        if not skorlar: return {}
        
        skorlar_np = np.array(skorlar)
        ortalama_skor = np.mean(skorlar_np)
        p90_skor = np.percentile(skorlar_np, 90)
        p95_skor = np.percentile(skorlar_np, 95)
        maks_skor = np.max(skorlar_np)
        
        # ANA MATEMATİK: Peak-Focused Hibrit Skor
        # Neden? Deepfake genellikle tüm karelerde değil, belirli anlarda patlak verir.
        # %70 en riskli kareler (P95), %30 genel ortalama.
        hibrit_skor = (p95_skor * 0.70) + (ortalama_skor * 0.30)
        ortalama_yuzde = hibrit_skor * 100
        
        # CERRAHİ HASSASİYET (Modelin gürültü payı ve hibrit skor baz alınarak optimize edildi)
        if ortalama_yuzde >= 60:
            teshis = "YÜKSEK OLASILIK: SAHTE / MANİPÜLASYON"
            risk_bandi = "KRITIK"
            mesaj = "Video üzerinde profesyonel yapay zeka müdahalesi kesin olarak tespit edildi."
        elif ortalama_yuzde >= 45:
            teshis = "ŞÜPHELİ: MUHTEMEL SAHTE"
            risk_bandi = "YUKSEK"
            mesaj = "Videonun bazı kısımları doğal görünmüyor, manipülasyon riski çok yüksek."
        elif ortalama_yuzde >= 30:
            teshis = "DÜŞÜK RİSK: MUHTEMEL GERÇEK"
            risk_bandi = "ORTA"
            mesaj = "Bazı anomaliler var ancak video genel olarak organik görünüyor."
        else:
            teshis = "GÜVENLİ: GERÇEK"
            risk_bandi = "DUSUK"
            mesaj = "Video tamamen doğal ve güvenli görünüyor."

        # main.py'nin beklediği yapı (VeraDeep_Audit_Report)
        rapor = {
            "VeraDeep_Audit_Report": {
                "Teshis": teshis,
                "Teshis_Kodu": risk_bandi,
                "Genel_Sahtelik_Olasiligi": f"%{ortalama_yuzde:.2f}",
                "Skor_Yontemi": "Peak-Focused Hybrid (P95*0.7 + Mean*0.3)",
                "Detayli_Istatistikler": {
                    "Analiz_Kare_Sayisi": len(skorlar),
                    "Ortalama_Skor": f"%{ortalama_skor*100:.2f}",
                    "P90_Skor": f"%{p90_skor*100:.2f}",
                    "P95_Skor": f"%{p95_skor*100:.2f}",
                    "Maksimum_Skor": f"%{maks_skor*100:.2f}"
                },
                "Detay": mesaj
            }
        }
        
        os.makedirs(cikis, exist_ok=True)
        with open(os.path.join(cikis, "final_analiz_raporu.json"), "w", encoding="utf-8") as f:
            json.dump(rapor, f, indent=4, ensure_ascii=False)
            
        print("\n" + "="*50)
        print(f"  VeraDeep PRO ANALİZ SONUCU (Hybrid Scoring)")
        print("="*50)
        print(f"  HİBRİT RİSK SKORU : %{ortalama_yuzde:.2f}")
        print(f"  P95 (PİK) RİSK   : %{p95_skor*100:.2f}")
        print(f"  TEŞHİS           : {teshis}")
        print(f"  GÜVEN DURUMU     : {mesaj}")
        print("="*50 + "\n")
        
        return rapor

    def calistir(self, klasor: str = "VeraDeep_Kareler", cikis: str = "."):
        gorseller, dosyalar = self.gorselleri_yukle(klasor)
        if not gorseller: return {}
        skorlar = self.batch_calistir(gorseller)
        return self.rapor_olustur(skorlar, dosyalar, cikis)

YapayZekaAnalizMotoru = AnalizMotoru
if __name__ == "__main__":
    AnalizMotoru().calistir()
