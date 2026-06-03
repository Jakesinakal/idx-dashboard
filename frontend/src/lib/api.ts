const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Snapshot {
  date: string;
  ihsg_close: number;
  ihsg_return_pct: number;
  usd_idr: number;
  fed_rate: number;
  cpi_us: number;
}

export interface Stock {
  ticker: string;
  name: string;
  close: number;
  volume: number;
  date: string;
  return_pct: number;
  ihsg_return_pct: number;
  vs_ihsg: "outperform" | "neutral" | "underperform";
}

export interface CurrencyPoint {
  date: string;
  usd_idr: number;
  eur_idr: number;
  jpy_idr: number;
}

export interface IHSGPoint {
  period: string;
  date: string;
  ihsg_close: number;
  change_pct: number;
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error on ${path}: ${res.status}`);
  return res.json();
}

export const fetchSnapshot = () => get<Snapshot>("/api/snapshot");
export const fetchStocks = () => get<Stock[]>("/api/stocks/today");
export const fetchCurrencyTrend = (days = 30) =>
  get<CurrencyPoint[]>(`/api/currency/trend?days=${days}`);
export const fetchIHSGComparison = () => get<IHSGPoint[]>("/api/ihsg/comparison");

// ── Formatters ────────────────────────────────────────────────────────────────

export function fmtNumber(n: number, decimals = 2) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtPct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function returnColor(n: number) {
  if (n > 0) return "text-emerald-400";
  if (n < 0) return "text-red-400";
  return "text-slate-400";
}
