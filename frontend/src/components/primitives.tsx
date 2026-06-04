// ============ Shared UI primitives ============
import { fmtPct } from "@/lib/format";
import type { Signal, Vs } from "@/lib/types";

// ---- Sentiment chip: + green / − red / • zinc ----
export function SentChip({ s, size = "sm" }: { s: number; size?: "sm" | "md" }) {
  const cfg =
    s > 0
      ? { ch: "+", cls: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10" }
      : s < 0
      ? { ch: "−", cls: "text-rose-400 border-rose-400/30 bg-rose-400/10" }
      : { ch: "•", cls: "text-zinc-400 border-zinc-700 bg-zinc-800/60" };
  const pad = size === "sm" ? "h-5 w-5 text-[11px]" : "h-6 w-6 text-xs";
  return (
    <span
      className={`inline-flex ${pad} items-center justify-center rounded-full border font-mono leading-none ${cfg.cls}`}
    >
      {cfg.ch}
    </span>
  );
}

// ---- Signal chip for the screener ----
export function SignalChip({ sig }: { sig: Signal }) {
  const map: Record<Signal, string> = {
    BUY: "text-emerald-400 border-emerald-400/30 bg-emerald-400/10",
    HOLD: "text-zinc-300 border-zinc-700 bg-zinc-800/70",
    SELL: "text-rose-400 border-rose-400/30 bg-rose-400/10",
    OB: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[11px] font-medium tracking-wide ${map[sig]}`}
    >
      {sig}
    </span>
  );
}

// ---- Delta value: colored number with arrow ----
export function Delta({
  pct,
  decimals = 2,
  className = "",
}: {
  pct: number;
  decimals?: number;
  className?: string;
}) {
  const color = pct >= 0 ? "text-emerald-400" : "text-rose-400";
  return (
    <span className={`font-mono tabular-nums ${color} ${className}`}>
      {fmtPct(pct, decimals)}
    </span>
  );
}

// ---- "vs IHSG" relative-strength label ----
export function VsChip({ vs }: { vs: Vs }) {
  const map: Record<Vs, string> = {
    Out: "text-emerald-400",
    Neutral: "text-zinc-400",
    Under: "text-rose-400",
  };
  return <span className={`font-mono text-xs ${map[vs]}`}>{vs}</span>;
}
