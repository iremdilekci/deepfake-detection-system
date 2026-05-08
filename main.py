import os
import json
import warnings
# Kendi yazdığımız gelişmiş modülleri içe aktarıyoruz
from video_kesici import VideoYuzKesici
from analiz_motoru import YapayZekaAnalizMotoru
from ses_motoru import VeraDeep as SenkronMotoru

warnings.filterwarnings("ignore")

# ===========================================================================
# ORKESTRA ŞEFİ (API / MAIN KONTROLCÜ)
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

        # --- TEK VE NIHAİ JSON ÇIKTISI ---
        nihai_rapor = {
            "VeraDeep_Nihai_Rapor": {
                "Gorsel_Risk_Skoru": round(gorsel_skor, 2),
                "Senkron_Risk_Skoru": round(senkron_skor, 2)
            }
        }
        
        with open("veradeep_nihai_rapor.json", "w", encoding="utf-8") as f:
            json.dump(nihai_rapor, f, indent=4, ensure_ascii=False)

        print("\n" + "="*50)
        print("VERADEEP UCTAN UCA ANALIZ SONUCU")
        print("="*50)
        print(f"Gorsel Hata Skoru : %{gorsel_skor:.2f}")
        print(f"Senkron Hata Skoru: %{senkron_skor:.2f}")
        print("="*50 + "\n")
        print("[BILGI] Rapor 'veradeep_nihai_rapor.json' olarak kaydedildi.")
        
        return nihai_rapor

    except Exception as e:
        print(f"[HATA] Raporlar okunamadi: {e}")
        return {}

if __name__ == "__main__":
    import sys
    import json
    hedef = sys.argv[1] if len(sys.argv) > 1 else "test.mp4"
    if os.path.exists(hedef):
        sonuc_json = sistemi_baslat(hedef)
        
        print("\n--- FRONTEND / NML İÇİN SAF JSON ÇIKTISI ---")
        # Frontend'in (veya NML'in) terminalden kolayca okuyabilmesi için
        # saf JSON formatında ekrana basıyoruz.
        print(json.dumps(sonuc_json, indent=4, ensure_ascii=False))
        print("--------------------------------------------\n")
    else:
        print(f"[HATA] {hedef} dosyasi bulunamadi!")