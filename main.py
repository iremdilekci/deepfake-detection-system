import video_kesici
import ai_motor
import json

def calistir():
    # 1. Video Karelere Bölünür (10 FPS)
    video_kesici.video_islem_merkezi(video_yolu="test.mp4", hedef_fps=10)

    # 2. Modeller Taramayı Yapar
    print("\n--- Analiz Safhası Başlıyor ---")
    rapor = ai_motor.analiz_et()

    # 3. Sonucu Ekrana Bas
    print("\n" + "="*40)
    print("🎯 VERA DEEP ANALİZ RAPORU")
    print("="*40)
    print(json.dumps(rapor, indent=4, ensure_ascii=False))
    print("\n[BİLGİ] Detaylı rapor 'analiz_sonucu.json' adıyla kaydedildi.")

if __name__ == "__main__":
    calistir()