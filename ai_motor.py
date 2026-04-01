import os
# TensorFlow uyarılarını gizle
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
import cv2
import numpy as np
import tensorflow as tf
import json
from datetime import datetime

# Modeli ve ağırlıkları hazırla
def modeli_yukle():
    base = tf.keras.applications.EfficientNetB0(include_top=False, weights='imagenet', input_shape=(224, 224, 3))
    x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    out = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    return tf.keras.Model(inputs=base.input, outputs=out)

model = modeli_yukle()

def analiz_et(klasor_yolu="VeraDeep_Kareler"):
    if not os.path.exists(klasor_yolu) or len(os.listdir(klasor_yolu)) == 0:
        return {"hata": "Analiz edilecek yüz bulunamadı!"}

    resimler = [f for f in os.listdir(klasor_yolu) if f.endswith('.jpg')]
    toplam_skor = 0.0 # Float olarak başlattık
    skor_listesi = []

    print(f"\n🔍 {len(resimler)} kare EfficientNet-B0 süzgecinden geçiyor...")
    print("⏳ Analiz yapılıyor, lütfen terminali kapatma...")

    for dosya in resimler:
        yol = os.path.join(klasor_yolu, dosya)
        img = cv2.imread(yol)
        if img is None: continue
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        img_array = np.expand_dims(img, axis=0) / 255.0
        
        # --- KRİTİK DÜZELTME: float() cast ekledik ---
        tahmin = model.predict(img_array, verbose=0)[0][0]
        skor_degeri = float(tahmin) # TensorFlow tipinden Python tipine çevirdik
        skor_listesi.append(skor_degeri)
        toplam_skor += skor_degeri

    # --- KARAR MEKANİZMASI ---
    ortalama_skor = toplam_skor / len(resimler)
    threshold = 0.50 
    
    is_fake = ortalama_skor > threshold
    karar = "🚨 DEEPFAKE (SAHTE)" if is_fake else "✅ GERÇEK (ORIGINAL)"

    # --- JSON ÇIKTISI (Artık hata vermeyecek) ---
    rapor = {
        "metadata": {
            "analiz_zamani": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "kullanilan_model": "EfficientNet-B0 (Pre-trained)",
            "toplam_islenen_kare": len(resimler)
        },
        "analiz_sonuclari": {
            "ortalama_guven_skoru": float(round(ortalama_skor, 4)),
            "esik_degeri": float(threshold),
            "en_yuksek_sahtelik_skoru": float(round(max(skor_listesi), 4)),
            "en_dusuk_sahtelik_skoru": float(round(min(skor_listesi), 4))
        },
        "nihai_karar": karar
    }

    # Dosyaya Kaydet
    with open("analiz_sonucu.json", "w", encoding="utf-8") as f:
        json.dump(rapor, f, indent=4, ensure_ascii=False)

    return rapor

if __name__ == "__main__":
    sonuc = analiz_et()
    print("\n" + "="*40)
    print(json.dumps(sonuc, indent=4, ensure_ascii=False))
    print("="*40)