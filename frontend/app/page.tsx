import Link from "next/link";

const analysisPillars = [
  {
    title: "Görüntü tutarlılığı",
    description:
      "Kareler arasındaki yapaylıkları, yüz detaylarındaki bozulmaları ve sahne içindeki uyumsuzlukları takip eder.",
  },
  {
    title: "Ses ve dudak uyumu",
    description:
      "Konuşma akışı ile dudak hareketleri arasındaki olası kaymaları işaretleyerek riskli kesitleri öne çıkarır.",
  },
  {
    title: "Metin ve bağlam sinyalleri",
    description:
      "Açıklama, yorum ve platform bağlamını birlikte okuyup şüpheli içerik desenlerini puanlar.",
  },
];

const quickSteps = [
  "İçerik dosya ya da bağlantı olarak sisteme gönderilir.",
  "Video, ses ve metin katmanları için ayrı inceleme adımları başlatılır.",
  "Sonuçlar güven skoru ve açıklanabilir içgörülerle yorumlanır.",
];

export default function Home() {
  return (
    <section className="px-5 pb-10 pt-10 sm:px-8 lg:px-10">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
        <div className="space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-indigo-50 px-4 py-2 text-sm font-medium text-indigo-700">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            TikTok, Instagram ve benzeri içerikler için çok modlu ön inceleme
          </div>

          <div className="max-w-2xl space-y-5">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
              Sosyal medyada paylaşılan videoları daha güvenli okumak için
              tasarlanmış bir inceleme platformu.
            </h1>
            <p className="max-w-xl text-base leading-8 text-slate-600 sm:text-lg">
              VeraDeep; görüntü, ses ve metin sinyallerini birlikte
              değerlendirerek şüpheli içerikleri analiz kuyruğuna alan ve sonucu
              açıklanabilir hale getirmeyi hedefleyen bir proje.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/analiz"
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold !text-white transition hover:bg-slate-800"
            >
              Analizi başlat
            </Link>
            <Link
              href="/nasil-calisir"
              className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-300 hover:bg-slate-50"
            >
              Nasıl çalıştığını gör
            </Link>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {analysisPillars.map((pillar) => (
              <article
                key={pillar.title}
                className="rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)]"
              >
                <p className="text-sm font-semibold text-slate-900">{pillar.title}</p>
                <p className="mt-2 text-sm leading-7 text-slate-600">{pillar.description}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-[32px] border border-slate-200 bg-slate-950 px-6 py-7 text-white shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <p className="text-sm font-medium text-slate-300">Neden VeraDeep?</p>
            <h2 className="mt-3 text-2xl font-semibold">
              Tek modlu yaklaşımlar yerine içeriği birkaç katmanda birlikte
              okumayı hedefler.
            </h2>
            <p className="mt-4 text-sm leading-7 text-slate-300">
              Sadece görüntüye bakmak çoğu zaman yeterli değildir. Sesin akışı,
              dudak hareketleri, açıklama metni ve kullanıcı etkileşimleri
              birlikte değerlendirildiğinde daha anlamlı bir güvenilirlik resmi
              ortaya çıkar.
            </p>
          </div>

          <div className="rounded-[32px] border border-white/70 bg-white/80 p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-slate-900">Süreç özeti</p>
            <ul className="mt-4 space-y-3">
              {quickSteps.map((step) => (
                <li key={step} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                  <span className="mt-2 h-2 w-2 rounded-full bg-emerald-500" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
