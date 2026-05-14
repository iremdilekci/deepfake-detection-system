import os
import json
import warnings
# Kendi yazdığımız gelişmiş modülleri içe aktarıyoruz
from video_kesici import VideoYuzKesici
from analiz_motoru import YapayZekaAnalizMotoru
from ses_motoru import VeraDeep as SenkronMotoru

warnings.filterwarnings("ignore")

# Görsel + Ses skorunu birleştirme; varsayılan AKTİF.
_FUZYON_ACIK = os.environ.get("VERADEEP_FUZYON", "1").strip().lower() in ("1", "true", "yes")

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
        # Yeni JSON yapısına göre okuma (VeraDeep_Audit_Report)
        with open("final_analiz_raporu.json", "r", encoding="utf-8") as f:
            gorsel_data = json.load(f)
            gorsel_skor = float(gorsel_data["VeraDeep_Audit_Report"]["Genel_Sahtelik_Olasiligi"].replace("%", ""))
        
        with open("senkron_analiz_raporu.json", "r", encoding="utf-8") as f:
            senkron_data = json.load(f)
            senkron_skor = float(senkron_data["VeraDeep_Sync_Report"]["final_risk_score"]) * 100

        if _FUZYON_ACIK:
            # Akıllı Füzyon v2: Daha hassas ve risk odaklı
            if gorsel_skor >= 70 or senkron_skor >= 85:
                # Bir kanal "kesin sahte" diyorsa onu baz al
                fusion_skor = max(gorsel_skor, senkron_skor)
            elif gorsel_skor >= 40 and senkron_skor >= 40:
                # Her iki kanal da "Şüpheli" diyorsa risk kümülatiftir
                fusion_skor = min(99.0, (gorsel_skor + senkron_skor) * 0.8)
            else:
                # Çelişki durumunda görsel ağırlığını artır (%70 görsel, %30 ses)
                fusion_skor = (gorsel_skor * 0.7) + (senkron_skor * 0.3)
            
            # Eşik değerini %50'den %45'e çekerek hassasiyeti artırıyoruz
            tahmin = "SAHTE" if fusion_skor >= 45 else "GERÇEK"
            tahmin_kaynagi = "fuzyon"
        else:
            fusion_skor = round(gorsel_skor, 2)
            tahmin = "SAHTE" if gorsel_skor >= 50 else "GERÇEK"
            tahmin_kaynagi = "yalnizca_gorsel"

        # --- TEK VE NIHAİ JSON ÇIKTISI ---
        nihai_rapor = {
            "VeraDeep_Nihai_Rapor": {
                "Gorsel_Risk_Skoru": round(gorsel_skor, 2),
                "Senkron_Risk_Skoru": round(senkron_skor, 2),
                "Fuzyon_Risk_Skoru": round(fusion_skor, 2),
                "Fuzyon_Aktif": _FUZYON_ACIK,
                "Tahmin_Kaynagi": tahmin_kaynagi,
                "Tahmin": tahmin,
            }
        }
        
        with open("veradeep_nihai_rapor.json", "w", encoding="utf-8") as f:
            json.dump(nihai_rapor, f, indent=4, ensure_ascii=False)

        print("\n" + "="*58)
        print("VERADEEP UCTAN UCA ANALIZ SONUCU")
        print("="*58)
        print(f"  VİDEO ADI         : {os.path.basename(video_adi)}")
        print(f"  GÖRSEL HATA SKORU : %{gorsel_skor:.2f}")
        print(f"  SES HATA SKORU    : %{senkron_skor:.2f}")
        if _FUZYON_ACIK:
            print(f"  FÜZYON SKORU      : %{fusion_skor:.2f}")
        else:
            print(f"  FÜZYON            : kapalı (tahmin sadece görsel; VERADEEP_FUZYON=1 ile açılır)")
            print(f"  (Fuzyon yerine görsel skoru yazıldı: %{fusion_skor:.2f})")
        print(f"  NİHAİ TAHMİN      : {tahmin}  [{tahmin_kaynagi}]")
        print("="*58 + "\n")
        print("[BILGI] Rapor 'veradeep_nihai_rapor.json' olarak kaydedildi.")
        
        return nihai_rapor

    except Exception as e:
        print(f"[HATA] Raporlar okunamadi: {e}")
        return {}

if __name__ == "__main__":
    import sys
    # Scriptin bulunduğu dizini al (Daha sağlam yol yönetimi)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    hedef = sys.argv[1] if len(sys.argv) > 1 else "test.mp4"
    
    # Eğer dosya tam yol değilse, scriptin dizininde aramayı dene
    if not os.path.isabs(hedef) and not os.path.exists(hedef):
        deneme_yolu = os.path.join(base_dir, hedef)
        if os.path.exists(deneme_yolu):
            hedef = deneme_yolu

    if os.path.exists(hedef):
        # Çalışma dizinini scriptin olduğu yere çek (Dosya yazma işlemleri için)
        os.chdir(base_dir)
        sonuc_json = sistemi_baslat(hedef)
        
        print("\n--- FRONTEND / NML İÇİN SAF JSON ÇIKTISI ---")
        print(json.dumps(sonuc_json, indent=4, ensure_ascii=False))
        print("--------------------------------------------\n")
    else:
        print(f"[HATA] {hedef} dosyasi bulunamadi!")
        print(f"[IPUCU] Dosyanın şurada olduğundan emin olun: {os.path.join(base_dir, 'test.mp4')}")