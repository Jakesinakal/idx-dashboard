"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { fetchCurrencyTrend, CurrencyPoint } from "@/lib/api";

// ── Period config ─────────────────────────────────────────────────────────────

type Period = "30d" | "ytd" | "1y";

const PERIODS: { key: Period; label: string; getDays: () => number }[] = [
  { key: "30d", label: "30D",  getDays: () => 30 },
  { key: "ytd", label: "YTD",  getDays: () => {
      const now = new Date();
      const startOfYear = new Date(now.getFullYear(), 0, 1);
      return Math.ceil((now.getTime() - startOfYear.getTime()) / 86_400_000);
    },
  },
  { key: "1y",  label: "1Y",   getDays: () => 365 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function shortDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function CurrencyTrend() {
  const [activePeriod, setActivePeriod] = useState<Period>("30d");
  const [data, setData] = useState<CurrencyPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const days = PERIODS.find((p) => p.key === activePeriod)!.getDays();
    fetchCurrencyTrend(days)
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [activePeriod]);

  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-5">
      {/* Header row */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-slate-400 text-xs uppercase tracking-wider">Currency Trend</h2>

        {/* Period toggle */}
        <div className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setActivePeriod(p.key)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                activePeriod === p.key
                  ? "bg-slate-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {loading || data.length === 0 ? (
        <div className="h-52 bg-slate-800 rounded animate-pulse" />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="date"
              tickFormatter={shortDate}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="idr"
              domain={["auto", "auto"]}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => (v / 1000).toFixed(0) + "k"}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                fontSize: 12,
              }}
              labelStyle={{ color: "#94a3b8", marginBottom: 4 }}
              labelFormatter={(label) => shortDate(label as string)}
              formatter={(value, name) => [
                typeof value === "number"
                  ? value.toLocaleString("en-US", { maximumFractionDigits: 0 })
                  : value,
                name,
              ]}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8", paddingTop: 16 }} />
            <Line
              yAxisId="idr"
              type="monotone"
              dataKey="usd_idr"
              name="USD/IDR"
              stroke="#60a5fa"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              yAxisId="idr"
              type="monotone"
              dataKey="eur_idr"
              name="EUR/IDR"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
