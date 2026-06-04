// ============ Data layer ============
// Fetches live data from the FastAPI backend and maps it to the view-model
// types the components consume. This is the single seam between the UI and the
// API: swapping data sources only touches this file.
//
// Base URL comes from NEXT_PUBLIC_API_URL (set in frontend/.env.local), falling
// back to the local dev backend. Fetches are uncached so the dashboard always
// reflects the latest warehouse data.

import type {
  BerandaData,
  IhsgPoint,
  Kpis,
  Mover,
  NewsItem,
  ScreenerRow,
  Signal,
  Trend,
  Universe,
  Vs,
} from "./types";
import { fullDateLabel, monthLabel, relativeTime } from "./format";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function getJson<T>(path: string): Promise<T> {
  // Cached ~5 min: the warehouse only updates once a day (Dagster run), so
  // caching makes navigation near-instant and lets Next dedupe the same fetch
  // across the layout + page — with negligible staleness.
  const res = await fetch(`${API_URL}${path}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new ApiError(`API ${path} -> ${res.status}`, res.status);
  return (await res.json()) as T;
}

// Coerce an arbitrary searchParam into a valid universe (default Semua).
export function normalizeUniverse(raw: string | string[] | undefined): Universe {
  return raw === "LQ45" || raw === "JII70" ? raw : "Semua";
}

// The backend uses "ALL" where the UI shows "Semua".
const toBackendUniverse = (u: Universe): string => (u === "Semua" ? "ALL" : u);

// Wrap a non-critical fetch: on any failure return a fallback instead of
// breaking the whole page (e.g. an empty news/movers table).
async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

// ---- Raw backend response shapes ----
interface RawSnapshot {
  date: string;
  ihsg_close: number;
  ihsg_return_pct: number;
  usd_idr: number;
  fed_rate: number;
  cpi_us: number;
  breadth: { advancers: number; decliners: number; unchanged: number; total: number } | null;
  sentiment: { mood: number; scored: number; positif: number; negatif: number; netral: number } | null;
}
interface RawHistPoint {
  date: string;
  ihsg_close: number;
}
interface RawMover {
  ticker: string;
  name: string;
  close: number;
  return_pct: number;
  signal: string;
}
interface RawMovers {
  gainers: RawMover[];
  losers: RawMover[];
}
interface RawNews {
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment_label: string | null;
  sentiment_score: number | null;
}
interface RawBriefing {
  date: string;
  narrative: string;
  ihsg_return_pct: number;
  news_mood: number | null;
  generated_at: string;
}
interface RawCurrencyPoint {
  date: string;
  usd_idr: number;
  eur_idr: number;
  jpy_idr: number;
}
interface RawScreenerRow {
  ticker: string;
  close: number;
  return_pct: number;
  rsi: number;
  ma_trend: string;
  momentum_pct: number;
  signal: string;
}

// ---- Field mappers ----
const stripJK = (ticker: string) => ticker.replace(/\.JK$/i, "");

function mapSignal(s: string): Signal {
  const v = s.toUpperCase();
  if (v === "OVERBOUGHT" || v === "OB") return "OB";
  if (v === "BUY" || v === "SELL") return v;
  return "HOLD";
}

const mapTrend = (t: string): Trend => (t.toLowerCase() === "bull" ? "bull" : "bear");

function mapVs(stockPct: number, ihsgPct: number): Vs {
  const diff = stockPct - ihsgPct;
  if (diff > 0.5) return "Out";
  if (diff < -0.5) return "Under";
  return "Neutral";
}

function sentimentSign(score: number | null, label: string | null): number {
  if (score != null) return score > 0 ? 1 : score < 0 ? -1 : 0;
  if (label === "positif") return 1;
  if (label === "negatif") return -1;
  return 0;
}

// One-day USD/IDR change (%) from the tail of the currency series.
function usdIdrChangePct(series: RawCurrencyPoint[]): number | null {
  if (series.length < 2) return null;
  const prev = series[series.length - 2].usd_idr;
  const last = series[series.length - 1].usd_idr;
  if (!prev) return null;
  return ((last - prev) / prev) * 100;
}

// ---- Page-level loaders ----

// Latest data date for the header, formatted "Selasa, 2 Jun 2026". Reuses the
// same cached /api/snapshot fetch as the pages, so request memoization makes it
// free when a page already loads the snapshot. Resilient (null on failure).
export async function getHeaderDate(): Promise<string | null> {
  try {
    const snap = await getJson<{ date?: string }>("/api/snapshot");
    return snap.date ? fullDateLabel(snap.date) : null;
  } catch {
    return null;
  }
}

export async function getBerandaData(universe: Universe = "Semua"): Promise<BerandaData> {
  const u = toBackendUniverse(universe);
  // snapshot is required (it anchors the KPIs); the rest degrade gracefully.
  const [snap, hist, movers, news, briefing, currency] = await Promise.all([
    getJson<RawSnapshot>("/api/snapshot"),
    safe(getJson<RawHistPoint[]>("/api/ihsg/history?days=90"), []),
    safe(getJson<RawMovers>(`/api/movers?universe=${u}&limit=3`), { gainers: [], losers: [] }),
    safe(getJson<RawNews[]>("/api/news?limit=7"), []),
    safe<RawBriefing | null>(getJson<RawBriefing>("/api/briefing"), null),
    safe(getJson<RawCurrencyPoint[]>("/api/currency/trend?days=7"), []),
  ]);

  const kpis: Kpis = {
    ihsg: { value: snap.ihsg_close, pct: snap.ihsg_return_pct },
    usdidr: { value: snap.usd_idr, pct: usdIdrChangePct(currency) },
    breadth: {
      up: snap.breadth?.advancers ?? 0,
      down: snap.breadth?.decliners ?? 0,
      flat: snap.breadth?.unchanged ?? 0,
    },
    sentiment: {
      score: snap.sentiment?.mood ?? 0,
      pos: snap.sentiment?.positif ?? 0,
      neg: snap.sentiment?.negatif ?? 0,
      net: snap.sentiment?.netral ?? 0,
    },
  };

  const series: IhsgPoint[] = hist.map((p, i) => ({
    i,
    label: monthLabel(p.date),
    value: p.ihsg_close,
  }));

  const gainers: Mover[] = movers.gainers.map((m) => ({ t: stripJK(m.ticker), pct: m.return_pct }));
  const losers: Mover[] = movers.losers.map((m) => ({ t: stripJK(m.ticker), pct: m.return_pct }));

  const newsItems: NewsItem[] = news.map((n) => ({
    s: sentimentSign(n.sentiment_score, n.sentiment_label),
    title: n.title,
    src: n.source,
    time: relativeTime(n.published_at),
    url: n.url,
  }));

  return {
    briefing: {
      narrative: briefing?.narrative ?? "",
      mood: briefing?.news_mood ?? snap.sentiment?.mood ?? null,
    },
    kpis,
    series,
    gainers,
    losers,
    news: newsItems,
  };
}

export async function getScreenerData(universe: Universe = "Semua"): Promise<ScreenerRow[]> {
  const u = toBackendUniverse(universe);
  // A universe with no stocks (e.g. JII70 before it's populated) yields a 404 —
  // treat that as "empty", but let any other failure bubble up to the error UI.
  let rows: RawScreenerRow[];
  try {
    rows = await getJson<RawScreenerRow[]>(`/api/screener?universe=${u}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return [];
    throw e;
  }
  const snap = await safe<RawSnapshot | null>(getJson<RawSnapshot>("/api/snapshot"), null);
  const ihsgPct = snap?.ihsg_return_pct ?? 0;
  return rows.map((r) => ({
    t: stripJK(r.ticker),
    price: r.close,
    pct: r.return_pct,
    rsi: r.rsi,
    trend: mapTrend(r.ma_trend),
    mom: r.momentum_pct,
    sig: mapSignal(r.signal),
    vs: mapVs(r.return_pct, ihsgPct),
  }));
}
