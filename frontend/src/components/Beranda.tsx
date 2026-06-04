// ============ HALAMAN 1 — BERANDA ============
import { fmt, fmtInt, fmtPct, fmtSigned } from "@/lib/format";
import { Delta, SentChip } from "@/components/primitives";
import { IhsgChart } from "@/components/IhsgChart";
import type { BerandaData } from "@/lib/types";

export default function Beranda({ data }: { data: BerandaData }) {
  const { briefing, kpis, series, gainers, losers, news } = data;
  const b = kpis.breadth;
  const totalBreadth = Math.max(1, b.up + b.down + b.flat);
  const sent = kpis.sentiment;
  const usd = kpis.usdidr;

  // Mood chip tone (hero)
  const mood = briefing.mood;
  const moodTone = mood == null ? "flat" : mood < 0 ? "neg" : mood > 0 ? "pos" : "flat";
  const moodChipCls = {
    neg: "border-rose-400/30 bg-rose-400/10 text-rose-400",
    pos: "border-emerald-400/30 bg-emerald-400/10 text-emerald-400",
    flat: "border-zinc-700 bg-zinc-800/60 text-zinc-400",
  }[moodTone];
  const moodLabel = moodTone === "neg" ? "cenderung negatif" : moodTone === "pos" ? "cenderung positif" : "netral";

  // USD/IDR — colored from the rupiah's perspective (up in USD = rupiah weaker).
  const rupiahWeaker = usd.pct != null && usd.pct > 0;
  const rupiahStronger = usd.pct != null && usd.pct < 0;
  const usdColor = rupiahWeaker ? "text-rose-400" : rupiahStronger ? "text-emerald-400" : "text-zinc-400";
  const usdLabel = rupiahWeaker ? "Rupiah melemah" : rupiahStronger ? "Rupiah menguat" : "";

  // Sentimen KPI
  const sentColor = sent.score < 0 ? "text-rose-400" : sent.score > 0 ? "text-emerald-400" : "text-zinc-400";
  const sentLabel = sent.score < 0 ? "cenderung negatif" : sent.score > 0 ? "cenderung positif" : "netral";

  return (
    <div className="mx-auto max-w-[1180px] px-6 py-8 sm:px-10">
      {/* HERO — Daily Summary */}
      <section
        className="relative overflow-hidden rounded-2xl border border-violet-500/20 p-7 sm:p-9"
        style={{ backgroundImage: "linear-gradient(to bottom, rgba(139,92,246,0.07), transparent)" }}
      >
        <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-violet-500/10 blur-3xl" />
        <div className="relative">
          <div className="mb-4 flex items-center gap-3">
            <span className="inline-flex items-center rounded-full border border-violet-400/40 bg-violet-400/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-widest text-violet-300">
              Daily Summary
            </span>
            {mood != null ? (
              <span className={`ml-auto inline-flex items-center gap-2 whitespace-nowrap rounded-full border px-3 py-1 text-xs ${moodChipCls}`}>
                <span className="font-mono">mood {fmtSigned(mood, 2)}</span>
                <span className="opacity-70">· {moodLabel}</span>
              </span>
            ) : null}
          </div>
          <p className="max-w-3xl text-[17px] leading-relaxed text-zinc-100 sm:text-lg">
            {briefing.narrative || "Briefing belum tersedia untuk hari ini."}
          </p>
        </div>
      </section>

      {/* KPI row */}
      <section className="mt-8 grid grid-cols-2 divide-zinc-800 border-y border-zinc-800 lg:grid-cols-4 lg:divide-x">
        <Kpi label="IHSG">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-semibold tabular-nums text-zinc-50">{fmt(kpis.ihsg.value)}</span>
            <Delta pct={kpis.ihsg.pct} />
          </div>
        </Kpi>
        <Kpi label="USD / IDR">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-semibold tabular-nums text-zinc-50">{fmtInt(usd.value)}</span>
            {usd.pct != null ? (
              <span className={`font-mono text-sm tabular-nums ${usdColor}`}>
                {fmtPct(usd.pct)}
              </span>
            ) : null}
          </div>
          {usdLabel ? <span className="mt-1 text-xs text-zinc-500">{usdLabel}</span> : null}
        </Kpi>
        <Kpi label="Breadth">
          <div className="font-mono text-2xl font-semibold tabular-nums text-zinc-50">
            <span className="text-emerald-400">{b.up}</span>
            <span className="text-zinc-600"> / </span>
            <span className="text-rose-400">{b.down}</span>
            <span className="text-zinc-600"> / </span>
            <span className="text-zinc-400">{b.flat}</span>
          </div>
          <div className="mt-2 flex h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div className="bg-emerald-400/80" style={{ width: `${(b.up / totalBreadth) * 100}%` }} />
            <div className="bg-zinc-600" style={{ width: `${(b.flat / totalBreadth) * 100}%` }} />
            <div className="bg-rose-400/80" style={{ width: `${(b.down / totalBreadth) * 100}%` }} />
          </div>
          <span className="mt-1.5 block text-xs text-zinc-500">naik · tetap · turun</span>
        </Kpi>
        <Kpi label="Sentimen">
          <div className="flex items-baseline gap-2">
            <span className={`font-mono text-2xl font-semibold tabular-nums ${sentColor}`}>{fmtSigned(sent.score, 2)}</span>
            <span className="text-xs text-zinc-500">{sentLabel}</span>
          </div>
          <span className="mt-1.5 block font-mono text-xs text-zinc-500">
            <span className="text-emerald-400">{sent.pos} pos</span> ·{" "}
            <span className="text-rose-400">{sent.neg} neg</span> ·{" "}
            <span className="text-zinc-400">{sent.net} net</span>
          </span>
        </Kpi>
      </section>

      {/* Chart + Top movers */}
      <section className="mt-8 grid grid-cols-1 gap-x-10 gap-y-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-zinc-200">IHSG · 90 hari</h3>
              <p className="text-xs text-zinc-500">Indeks Harga Saham Gabungan</p>
            </div>
            <Delta pct={kpis.ihsg.pct} className="text-sm" />
          </div>
          <div className="h-64 w-full">
            {series.length > 0 ? (
              <IhsgChart series={series} />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-zinc-600">Data chart tidak tersedia</div>
            )}
          </div>
        </div>

        {/* Top Movers */}
        <div>
          <h3 className="mb-4 text-sm font-medium text-zinc-200">Top Movers</h3>
          <div className="space-y-5">
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-emerald-400">
                Gainers
              </div>
              <div className="divide-y divide-zinc-800/80 border-y border-zinc-800/80">
                {gainers.map((g) => (
                  <MoverRow key={g.t} t={g.t} pct={g.pct} />
                ))}
              </div>
            </div>
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-rose-400">
                Losers
              </div>
              <div className="divide-y divide-zinc-800/80 border-y border-zinc-800/80">
                {losers.map((g) => (
                  <MoverRow key={g.t} t={g.t} pct={g.pct} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Berita & Sentimen */}
      <section className="mt-10">
        <h3 className="mb-4 text-sm font-medium text-zinc-200">Berita &amp; Sentimen</h3>
        <div className="divide-y divide-zinc-800 border-t border-zinc-800">
          {news.map((n, i) => (
            <a
              key={i}
              href={n.url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-4 py-3.5 transition-colors hover:bg-zinc-900/60"
            >
              <SentChip s={n.s} />
              <span className="flex-1 text-[15px] text-zinc-200 group-hover:text-zinc-50">{n.title}</span>
              <span className="hidden shrink-0 font-mono text-xs text-zinc-500 sm:block">{n.src}</span>
              <span className="w-14 shrink-0 text-right font-mono text-xs text-zinc-600">{n.time}</span>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="px-0 py-4 lg:px-6 lg:first:pl-0">
      <div className="mb-1.5 text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</div>
      {children}
    </div>
  );
}

function MoverRow({ t, pct }: { t: string; pct: number }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="font-mono text-sm font-medium text-zinc-100">{t}</span>
      <Delta pct={pct} decimals={1} className="text-sm" />
    </div>
  );
}
