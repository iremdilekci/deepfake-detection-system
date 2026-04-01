import cv2
import os
import shutil

def video_islem_merkezi(video_yolu="test.mp4", cikis_klasoru="VeraDeep_Kareler", hedef_fps=10):
    """
    Videoyu saniyede 10 kareye böler, sadece yüzü keser ve kaydeder.
    """
    print(f"\n🚀 [SİSTEM] Standart Video İşleme Başlatıldı. Hedef: {hedef_fps} FPS")

    # 1. Dosya ve Klasör Kontrolü
    if not os.path.exists(video_yolu):
        print(f"❌ [HATA] '{video_yolu}' bulunamadı!")
        return

    if os.path.exists(cikis_klasoru):
        shutil.rmtree(cikis_klasoru)
    os.makedirs(cikis_klasoru)

    # 2. Yüz Tanıma Hazırlığı
    yuz_cascadi = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(video_yolu)
    orijinal_fps = cap.get(cv2.CAP_PROP_FPS)
    if orijinal_fps <= 0: orijinal_fps = 30
    
    atlama_araligi = max(1, int(orijinal_fps / hedef_fps))
    
    kare_sayisi = 0
    kaydedilen_yuz = 0

    print(f"📂 [İŞLEM] '{video_yolu}' işleniyor. Filtreler devre dışı bırakıldı.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if kare_sayisi % atlama_araligi == 0:
            gri = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            yuzler = yuz_cascadi.detectMultiScale(gri, 1.1, 5, minSize=(40, 40))

            for (x, y, w, h) in yuzler:
                # Sadece tespit edilen bölgeyi kesiyoruz (Ekstra pay/padding yok)
                yuz_kesimi = frame[y:y+h, x:x+w]
                
                # Standart boyutlandırma (Hızlı ve basit)
                yuz_resize = cv2.resize(yuz_kesimi, (224, 224))
                
                # Kaydet
                dosya_adi = os.path.join(cikis_klasoru, f"yuz_{kaydedilen_yuz}.jpg")
                cv2.imwrite(dosya_adi, yuz_resize)
                kaydedilen_yuz += 1

        kare_sayisi += 1

    cap.release()
    
    if kaydedilen_yuz > 0:
        print(f"✅ [TAMAMLANDI] {kaydedilen_yuz} adet yüz olduğu gibi kaydedildi.")
    else:
        print("⚠️ [UYARI] Videoda hiç yüz tespit edilemedi.")

if __name__ == "__main__":
    video_islem_merkezi()