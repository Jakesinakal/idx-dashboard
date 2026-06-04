// ============ View-model types (shared by the data layer + components) ============

export type Signal = "BUY" | "HOLD" | "SELL" | "OB";
export type Trend = "bull" | "bear";
export type Vs = "Out" | "Neutral" | "Under";

export const UNIVERSES = ["LQ45", "JII70", "Semua"] as const;
export type Universe = (typeof UNIVERSES)[number];

export interface IhsgPoint {
  i: number;
  label: string;
  value: number;
}

export interface Kpis {
  ihsg: { value: number; pct: number };
  usdidr: { value: number; pct: number | null };
  breadth: { up: number; down: number; flat: number };
  sentiment: { score: number; pos: number; neg: number; net: number };
}

export interface Mover {
  t: string;
  pct: number;
}

export interface NewsItem {
  s: number; // sentiment: +1 / 0 / -1
  title: string;
  src: string;
  time: string;
  url: string;
}

export interface ScreenerRow {
  t: string;
  price: number;
  pct: number;
  rsi: number;
  trend: Trend;
  mom: number;
  sig: Signal;
  vs: Vs;
}

export interface Briefing {
  narrative: string;
  mood: number | null;
}

export interface BerandaData {
  briefing: Briefing;
  kpis: Kpis;
  series: IhsgPoint[];
  gainers: Mover[];
  losers: Mover[];
  news: NewsItem[];
}
