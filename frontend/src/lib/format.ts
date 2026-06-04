// Indonesian number + date formatting.
// Negatives use the Unicode minus "−" (U+2212) to match the design.

export function fmt(n: number, decimals = 2): string {
  return new Intl.NumberFormat("id-ID", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n);
}

export function fmtInt(n: number): string {
  return new Intl.NumberFormat("id-ID", { maximumFractionDigits: 0 }).format(n);
}

export function fmtPct(n: number, decimals = 2): string {
  const s = n > 0 ? "+" : n < 0 ? "−" : "";
  return s + fmt(Math.abs(n), decimals) + "%";
}

export function fmtSigned(n: number, decimals = 2): string {
  const s = n > 0 ? "+" : n < 0 ? "−" : "";
  return s + fmt(Math.abs(n), decimals);
}

const MONTH_SHORT = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

// "2026-03-04" (or ISO datetime) -> "4 Mar"
export function monthLabel(iso: string): string {
  const [y, m, d] = iso.split("T")[0].split("-").map(Number);
  void y;
  return `${d} ${MONTH_SHORT[(m - 1 + 12) % 12]}`;
}

const DAY_ID = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];

// "2026-06-02" -> "Selasa, 2 Jun 2026"
export function fullDateLabel(iso: string): string {
  const [y, m, d] = iso.split("T")[0].split("-").map(Number);
  if (!y || !m || !d) return "";
  const day = DAY_ID[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  return `${day}, ${d} ${MONTH_SHORT[(m - 1 + 12) % 12]} ${y}`;
}

// ISO timestamp -> compact relative age, e.g. "5 jam", "2 hari".
export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const sec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  const min = Math.floor(sec / 60);
  const hr = Math.floor(min / 60);
  const day = Math.floor(hr / 24);
  if (day >= 1) return `${day} hari`;
  if (hr >= 1) return `${hr} jam`;
  if (min >= 1) return `${min} mnt`;
  return "baru";
}
