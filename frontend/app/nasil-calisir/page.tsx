const steps = [
  {
    step: "01",
    title: "İçerik sisteme alınır",
    description:
      "Kullanıcı video dosyası yükler veya sosyal medya bağlantısı ekler. İlk aşamada içerik doğrulanır ve analiz kuyruğuna alınır.",
  },
  {
    step: "02",
    title: "Katmanlı inceleme başlar",
    description:
      "Görüntü kareleri, ses akışı ve metinsel bağlam birbirinden bağımsız sinyaller olarak işlenir.",
  },
  {
    step: "03",
    title: "Sinyaller birleştirilir",
    description:
      "Çok modlu bulgular aynı havuzda toplanır ve tutarsızlıkların ortak örüntüleri çıkarılır.",
  },
  {
    step: "04",
    title: "Açıklanabilir çıktı üretilir",
    description:
      "Sistemin amacı yalnızca bir skor vermek değil, hangi nedenle risk oluştuğunu da anlaşılır biçimde sunmaktır.",
  },
];

export default function HowItWorksPage() {
  return (
    <section className="px-5 pb-10 pt-10 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="max-w-3xl space-y-4">
          <p className="text-sm font-medium text-indigo-700">Nasıl çalışır?</p>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
            VeraDeep analiz akışını birbirini tamamlayan birkaç adıma bölerek ilerler.
          </h1>
          <p className="text-base leading-8 text-slate-600">
            Bu sayfa ürün mantığını teknik ayrıntıya boğmadan anlatır. Amaç,
            kullanıcının içerik sisteme girdikten sonra ne olduğunu kolayca anlayabilmesidir.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {steps.map((item) => (
            <article
              key={item.step}
              className="rounded-[32px] border border-white/70 bg-white/85 p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)]"
            >
              <p className="text-sm font-semibold text-indigo-600">{item.step}</p>
              <h2 className="mt-3 text-2xl font-semibold text-slate-950">{item.title}</h2>
              <p className="mt-3 text-sm leading-7 text-slate-600">{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
