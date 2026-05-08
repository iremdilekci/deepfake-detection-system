import Link from "next/link";

const navItems = [
  { href: "/", label: "Ana Sayfa" },
  { href: "/analiz", label: "Analiz" },
  { href: "/nasil-calisir", label: "Nasıl Çalışır" },
  { href: "/hakkinda", label: "Hakkında" },
];

export default function SiteHeader() {
  return (
    <header className="px-5 pt-6 sm:px-8 lg:px-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 rounded-[28px] border border-white/70 bg-white/80 px-5 py-4 shadow-[0_10px_30px_rgba(15,23,42,0.06)] backdrop-blur sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/10">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-900">
              VeraDeep
            </p>
            <p className="text-xs text-slate-500">
              Çok modlu deepfake inceleme arayüzü
            </p>
          </div>
        </Link>

        <nav className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-4 py-2 transition hover:bg-slate-100 hover:text-slate-900"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
