"use client";

// ============ HALAMAN 2 — SCREENER ============
import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronDown, ChevronUp, Search } from "lucide-react";
import { fmtInt, fmtPct } from "@/lib/format";
import { SignalChip, VsChip } from "@/components/primitives";
import { UNIVERSES, type ScreenerRow, type Universe } from "@/lib/types";

type SortKey = keyof ScreenerRow;
type Align = "left" | "right" | "center";

const SIG_TABS = ["ALL", "BUY", "HOLD", "SELL", "OB"] as const;

const COLS: { k: SortKey; label: string; align: Align }[] = [
  { k: "t", label: "Ticker", align: "left" },
  { k: "price", label: "Harga", align: "right" },
  { k: "pct", label: "%1H", align: "right" },
  { k: "rsi", label: "RSI", align: "right" },
  { k: "trend", label: "MA Trend", align: "right" },
  { k: "mom", label: "Momentum", align: "right" },
  { k: "sig", label: "Sinyal", align: "center" },
  { k: "vs", label: "vs IHSG", align: "center" },
];

export default function Screener({ rows: allRows, universe }: { rows: ScreenerRow[]; universe: Universe }) {
  const router = useRouter();
  const [uniOpen, setUniOpen] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("t");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [sigFilter, setSigFilter] = useState<string>("ALL");
  const [q, setQ] = useState("");

  // Universe drives a server re-fetch via the URL (avoids a browser→API call,
  // so CORS never comes into play).
  function selectUniverse(u: Universe) {
    setUniOpen(false);
    router.push(u === "Semua" ? "/screener" : `/screener?u=${u}`);
  }

  const rows = useMemo(() => {
    let r = allRows.slice();
    if (sigFilter !== "ALL") r = r.filter((x) => x.sig === sigFilter);
    if (q.trim()) r = r.filter((x) => x.t.toLowerCase().includes(q.trim().toLowerCase()));
    const dir = sortDir === "asc" ? 1 : -1;
    r.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string" && typeof bv === "string") return av.localeCompare(bv) * dir;
      return ((av as number) - (bv as number)) * dir;
    });
    return r;
  }, [allRows, sortKey, sortDir, sigFilter, q]);

  function toggleSort(k: SortKey) {
    if (sortKey === k) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      setSortDir(k === "t" ? "asc" : "desc");
    }
  }

  return (
    <div className="mx-auto max-w-[1180px] px-6 py-8 sm:px-10">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-medium text-zinc-100">Screener</h2>
          <p className="text-sm text-zinc-500">
            {rows.length} dari {allRows.length} saham · klik header untuk mengurutkan
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* universe filter */}
          <div className="relative">
            <button
              onClick={() => setUniOpen((o) => !o)}
              onBlur={() => setTimeout(() => setUniOpen(false), 120)}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 font-mono text-sm text-zinc-200 transition-colors hover:border-zinc-700"
            >
              {universe}
              <ChevronDown size={14} className="text-zinc-500" />
            </button>
            {uniOpen ? (
              <div className="absolute left-0 top-full z-30 mt-1.5 w-32 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 py-1 shadow-xl shadow-black/40">
                {UNIVERSES.map((u) => (
                  <button
                    key={u}
                    onMouseDown={() => selectUniverse(u)}
                    className={`flex w-full items-center justify-between px-3 py-1.5 text-left font-mono text-xs transition-colors hover:bg-zinc-800 ${
                      universe === u ? "text-violet-300" : "text-zinc-300"
                    }`}
                  >
                    {u}
                    {universe === u ? <Check size={13} /> : null}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          {/* search */}
          <div className="relative">
            <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Cari ticker…"
              className="h-9 w-40 rounded-lg border border-zinc-800 bg-zinc-900/60 pl-8 pr-3 font-mono text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-violet-500/50 focus:outline-none focus:ring-1 focus:ring-violet-500/30"
            />
          </div>
          {/* signal filter */}
          <div className="flex items-center rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5">
            {SIG_TABS.map((s) => (
              <button
                key={s}
                onClick={() => setSigFilter(s)}
                className={`rounded-md px-2.5 py-1.5 font-mono text-xs transition-colors ${
                  sigFilter === s ? "bg-zinc-800 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {s === "ALL" ? "Semua" : s}
              </button>
            ))}
          </div>

          {/* mobile sort — desktop uses the clickable table headers instead */}
          <div className="flex w-full items-center gap-2 sm:hidden">
            <span className="shrink-0 text-xs text-zinc-500">Urut</span>
            <select
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="h-9 flex-1 rounded-lg border border-zinc-800 bg-zinc-900/60 px-2 font-mono text-sm text-zinc-200 focus:border-violet-500/50 focus:outline-none"
            >
              {COLS.map((c) => (
                <option key={c.k} value={c.k}>
                  {c.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
              aria-label="Balik arah urutan"
              className="flex h-9 shrink-0 items-center rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 text-zinc-200 transition-colors hover:border-zinc-700"
            >
              {sortDir === "asc" ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
          </div>
        </div>
      </div>

      {/* mobile: card list (the table is hard to scan on a phone) */}
      <div className="space-y-2.5 sm:hidden">
        {rows.map((r) => (
          <ScreenerCard key={r.t} r={r} />
        ))}
      </div>

      {/* desktop: table */}
      <div className="hidden overflow-x-auto sm:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-y border-zinc-800">
              {COLS.map((c) => (
                <th
                  key={c.k}
                  onClick={() => toggleSort(c.k)}
                  className={`cursor-pointer select-none whitespace-nowrap px-4 py-2.5 text-xs font-medium uppercase tracking-wider text-zinc-500 transition-colors hover:text-zinc-300 ${
                    c.align === "right" ? "text-right" : c.align === "center" ? "text-center" : "text-left"
                  }`}
                >
                  <span className={`inline-flex items-center gap-1 ${c.align === "right" ? "flex-row-reverse" : ""}`}>
                    {c.label}
                    {sortKey === c.k ? (
                      sortDir === "asc" ? (
                        <ChevronUp size={13} className="text-violet-400" />
                      ) : (
                        <ChevronDown size={13} className="text-violet-400" />
                      )
                    ) : null}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.t} className="border-b border-zinc-800/60 transition-colors hover:bg-zinc-900/50">
                <td className="px-4 py-3 font-mono font-medium text-zinc-100">{r.t}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-200">{fmtInt(r.price)}</td>
                <td className={`px-4 py-3 text-right font-mono tabular-nums ${r.pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {fmtPct(r.pct, 1)}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">
                  <span className={r.rsi >= 70 ? "text-amber-400" : r.rsi <= 30 ? "text-rose-400" : "text-zinc-300"}>
                    {r.rsi}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={`font-mono text-xs ${r.trend === "bull" ? "text-emerald-400" : "text-rose-400"}`}>
                    {r.trend === "bull" ? "Bull" : "Bear"}
                  </span>
                </td>
                <td className={`px-4 py-3 text-right font-mono tabular-nums ${r.mom >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {fmtPct(r.mom, 1)}
                </td>
                <td className="px-4 py-3 text-center">
                  <SignalChip sig={r.sig} />
                </td>
                <td className="px-4 py-3 text-center">
                  <VsChip vs={r.vs} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {rows.length === 0 ? (
        <div className="py-16 text-center text-sm text-zinc-500">Tidak ada saham yang cocok.</div>
      ) : null}
    </div>
  );
}

// Mobile row rendered as a card — same data as a table row, easier to scan on a phone.
function ScreenerCard({ r }: { r: ScreenerRow }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3.5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-base font-semibold text-zinc-100">{r.t}</span>
        <span className="font-mono tabular-nums text-zinc-200">{fmtInt(r.price)}</span>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-center">
        <Stat label="%1H">
          <span className={r.pct >= 0 ? "text-emerald-400" : "text-rose-400"}>{fmtPct(r.pct, 1)}</span>
        </Stat>
        <Stat label="RSI">
          <span className={r.rsi >= 70 ? "text-amber-400" : r.rsi <= 30 ? "text-rose-400" : "text-zinc-300"}>{r.rsi}</span>
        </Stat>
        <Stat label="Trend">
          <span className={r.trend === "bull" ? "text-emerald-400" : "text-rose-400"}>{r.trend === "bull" ? "Bull" : "Bear"}</span>
        </Stat>
        <Stat label="Mom">
          <span className={r.mom >= 0 ? "text-emerald-400" : "text-rose-400"}>{fmtPct(r.mom, 1)}</span>
        </Stat>
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-zinc-800/60 pt-3">
        <SignalChip sig={r.sig} />
        <span className="flex items-center gap-1.5 text-xs text-zinc-500">
          vs IHSG <VsChip vs={r.vs} />
        </span>
      </div>
    </div>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-zinc-600">{label}</div>
      <div className="mt-0.5 font-mono text-sm tabular-nums">{children}</div>
    </div>
  );
}
