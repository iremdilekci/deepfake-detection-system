const goals = [
  "Sosyal medya içeriklerinin güvenilirliğini daha anlaşılır hale getirmek",
  "Görüntü, ses ve metin sinyallerini birlikte değerlendirmek",
  "LLM destekli yorum katmanıyla açıklanabilir sonuç üretmek",
];

export default function AboutPage() {
  return (
    <section className="px-5 pb-10 pt-10 sm:px-8 lg:px-10">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-5">
          <p className="text-sm font-medium text-indigo-700">Proje hakkında</p>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">
            VeraDeep, artan deepfake içeriklerine karşı çok modlu bir değerlendirme yaklaşımı önerir.
          </h1>
          <p className="text-base leading-8 text-slate-600">
            Günümüzde özellikle TikTok ve Instagram gibi sosyal medya
            platformlarında paylaşılan içeriklerin gerçekliğini ayırt etmek
            giderek zorlaşıyor. VeraDeep; video karelerindeki görsel
            tutarsızlıkları, ses ile dudak senkronunu ve açıklama ya da yorum
            metinlerini birlikte inceleyerek daha kapsamlı bir güvenilirlik
            çerçevesi üretmeyi hedefler.
          </p>
          <p className="text-base leading-8 text-slate-600">
            Proje adını, &quot;Veritas&quot; yani gerçeklik kavramı ile deep learning
            yaklaşımını bir araya getiren bir anlamdan alır. Teknik hedef kadar
            önemli olan diğer hedef ise sonucu kullanıcı için açıklanabilir ve
            güven verici biçimde sunmaktır.
          </p>
        </div>

        <div className="space-y-4">
          <section className="rounded-[32px] border border-slate-200 bg-slate-950 px-6 py-7 text-white shadow-[0_24px_80px_rgba(15,23,42,0.16)]">
            <p className="text-sm font-medium text-slate-300">Temel amaç</p>
            <p className="mt-3 text-2xl font-semibold">
              Yanlış bilginin yayılmasını azaltırken içerik güvenilirliğini artırmak.
            </p>
          </section>

          <section className="rounded-[32px] border border-white/70 bg-white/85 p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
            <p className="text-sm font-semibold text-slate-900">Öne çıkan hedefler</p>
            <ul className="mt-4 space-y-3">
              {goals.map((goal) => (
                <li key={goal} className="flex items-start gap-3 text-sm leading-7 text-slate-600">
                  <span className="mt-2 h-2 w-2 rounded-full bg-emerald-500" />
                  <span>{goal}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </section>
  );
}
