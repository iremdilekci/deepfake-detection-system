export default function SiteFooter() {
  return (
    <footer className="px-5 pb-8 pt-12 sm:px-8 lg:px-10">
      <div className="mx-auto grid max-w-6xl gap-6 rounded-[32px] border border-white/70 bg-white/75 px-6 py-6 shadow-[0_12px_36px_rgba(15,23,42,0.05)] md:grid-cols-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">VeraDeep</p>
          <p className="mt-2 text-sm leading-7 text-slate-600">
            Video, ses ve metin sinyallerini birlikte değerlendirerek daha
            açıklanabilir bir deepfake inceleme deneyimi sunmayı hedefler.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Odak alanları</p>
          <p className="mt-2 text-sm leading-7 text-slate-600">
            Görsel tutarlılık analizi, ses ve dudak senkronu, açıklama ve
            yorum bağlamı değerlendirmesi.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Durum</p>
          <p className="mt-2 text-sm leading-7 text-slate-600">
            Bu arayüz sprint demosu için hazırlanmış ilk ürün katmanıdır ve
            analiz kuyruğuna içerik göndermeyi destekler.
          </p>
        </div>
      </div>
    </footer>
  );
}
