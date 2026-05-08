export default function Loading() {
  return (
    <section className="px-5 pb-10 pt-10 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl animate-pulse space-y-6">
        <div className="h-6 w-40 rounded-full bg-slate-200" />
        <div className="h-16 max-w-3xl rounded-[28px] bg-slate-200" />
        <div className="grid gap-4 md:grid-cols-2">
          <div className="h-48 rounded-[32px] bg-white/80 shadow-[0_18px_50px_rgba(15,23,42,0.04)]" />
          <div className="h-48 rounded-[32px] bg-white/80 shadow-[0_18px_50px_rgba(15,23,42,0.04)]" />
        </div>
      </div>
    </section>
  );
}
