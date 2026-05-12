# VeraDeep - Database Partitioning ve Archiving Planı

Bu belge, VeraDeep Deepfake Tespit Sistemi'nin zamanla büyüyecek olan veri tabanı tabloları (`videos` ve `analysis_results`) için disk performansını korumak, arama maliyetlerini düşürmek ve depolama alanını optimize etmek amacıyla oluşturulmuş Partitioning (Bölümleme) ve Archiving (Arşivleme) stratejisini içerir.

## 1. Mevcut Durum ve Sorun
Sistem her bir analiz isteği için:
1. `videos` tablosuna bir video meta verisi kaydı ekler.
2. İşlem tamamlandığında `analysis_results` tablosuna ağır bir JSON (modaliteler, LLM açıklaması, zaman serisi chart verileri vb.) içeren geniş bir kayıt ekler.
3. Fiziksel medya dosyalarını sunucuda (veya bulutta) tutar.

Zamanla, her gün binlerce analiz yapıldığında `analysis_results` tablosu devasa boyutlara ulaşacak ve:
- B-Tree index'leri RAM'e sığmayacak, sorgular yavaşlayacaktır.
- Yedekleme (Backup) ve Geri Yükleme (Restore) süreleri çok uzayacaktır.
- Bulut veritabanı (RDS/Cloud SQL) depolama maliyetleri artacaktır.

---

## 2. Partitioning (Bölümleme) Stratejisi

PostgreSQL'in **Declarative Partitioning (Range Partitioning)** özelliği kullanılarak tablolar zamana dayalı (aylık) parçalara ayrılacaktır.

### A. Uygulanacak Tablolar
- **`videos` Tablosu:**
  `created_at` kolonuna göre partition yapılacaktır.
- **`analysis_results` Tablosu:**
  Bu tablo `videos` tablosu ile 1-to-many (veya 1-1) ilişkilidir. Aynı şekilde `created_at` (veya `video_id` üzerinden gelen tarih) baz alınarak partition yapılacaktır.

### B. Partitioning Yöntemi
- **Tip:** `RANGE (created_at)`
- **Periyot:** Aylık (Örn: `videos_2026_05`, `videos_2026_06`)
- **Otomasyon:** `pg_partman` eklentisi (veya özel bir background worker) kullanılarak her ayın sonunda bir sonraki ayın partition tabloları otomatik olarak oluşturulacaktır.

### C. Örnek SQL (PostgreSQL)
```sql
-- Ana tabloyu partition yapısı ile oluşturma
CREATE TABLE analysis_results (
    id UUID NOT NULL,
    video_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    details JSONB,
    ...
) PARTITION BY RANGE (created_at);

-- Aylık partition oluşturma
CREATE TABLE analysis_results_2026_05 PARTITION OF analysis_results 
    FOR VALUES FROM ('2026-05-01 00:00:00') TO ('2026-06-01 00:00:00');
```

---

## 3. Archiving (Arşivleme) ve Veri Saklama (Retention) Stratejisi

Sıcak veritabanını (Hot Storage) temiz tutmak için eski veriler belirli bir ömürden sonra daha ucuz bir depolama katmanına (Cold Storage) taşınacaktır.

### A. Veritabanı Arşivleme (Database Archiving)
- **Kural:** 6 aydan daha eski analiz sonuçları aktif PostgreSQL sunucusundan arşivlenecektir.
- **Yöntem:**
  1. 6 aylık ömrünü dolduran eski partition (örn: `analysis_results_2025_11`) PostgreSQL'den `DETACH` edilir.
  2. Detach edilen tablo verisi `pg_dump` veya Parquet formatında dışa aktarılır.
  3. Çıkarılan dosya AWS S3 / Google Cloud Storage gibi ucuz bir object storage servisine "Glacier/Coldline" sınıfında kaydedilir.
  4. Detach edilen tablo PostgreSQL'den `DROP` edilerek disk alanı geri kazanılır.

### B. Fiziksel Dosya Arşivleme (File Storage Cleanup)
Yüklenen `.mp4` / `.webm` vb. dosyalar çok hızlı bir şekilde disk alanını tüketecektir.
- **Kural:** Analiz tamamlandıktan sonra ve sonuç kullanıcıya gösterildikten (veya belirli bir grace period -örn. 7 gün- geçtikten) sonra kaynak medya dosyaları otomatik olarak silinmelidir.
- Sadece `source_url` bilgisi ve `analysis_results` JSON verisi veritabanında tarihsel (historical) olarak tutulmalıdır.

---

## 4. İleride Yapılacak Eylem Planı (Implementation Steps)

1. **Alembic Migration:** Mevcut `videos` ve `analysis_results` tabloları için veriyi yeni Partitioned tablolara aktaracak bir veri taşıma script'i (migration) yazılması.
2. **Cron Job / Celery Worker:** Her gün gece çalışarak 7 günü geçmiş fiziksel medya dosyalarını sunucudan silecek bir temizlik (cleanup) worker'ının projeye eklenmesi.
3. **Partition Otomasyonu:** PostgreSQL'de `pg_partman` extension'ının kurularak partition bakım işlemlerinin (yeni tablo oluşturma, eskileri detach etme) otomatikleştirilmesi.
