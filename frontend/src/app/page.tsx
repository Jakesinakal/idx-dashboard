"use client";

import { useEffect, useState } from "react";
import {
  fetchSnapshot,
  fetchStocks,
  fetchIHSGComparison,
  Snapshot,
  Stock,
  IHSGPoint,
} from "@/lib/api";
import MarketSnapshot from "@/components/MarketSnapshot";
import StockPerformance from "@/components/StockPerformance";
import IHSGComparison from "@/components/IHSGComparison";
import CurrencyTrend from "@/components/CurrencyTrend";

export default function Dashboard() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [ihsgComparison, setIhsgComparison] = useState<IHSGPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      fetchSnapshot(),
      fetchStocks(),
      fetchIHSGComparison(),
    ]).then(([snapRes, stksRes, compRes]) => {
      if (snapRes.status === "fulfilled") setSnapshot(snapRes.value);
      if (stksRes.status === "fulfilled") setStocks(stksRes.value);
      if (compRes.status === "fulfilled") setIhsgComparison(compRes.value);

      const failed = [snapRes, stksRes, compRes].filter(
        (r): r is PromiseRejectedResult => r.status === "rejected"
      );
      if (failed.length)
        setError(failed[0].reason?.message ?? "Some data failed to load");
    });
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-white">Finance Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">
          {snapshot ? `As of ${snapshot.date} · IDX + US Macroeconomics` : "Loading data..."}
        </p>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-4 rounded-lg bg-red-900/20 border border-red-500/30 text-red-400 text-sm">
          Failed to load data: {error}
        </div>
      )}

      <div className="space-y-4">
        {/* Row 1: Market Snapshot — 4 metric cards */}
        <MarketSnapshot data={snapshot} />

        {/* Row 2: Stock Performance (left) + IHSG Comparison (right) */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-3">
            <StockPerformance data={stocks} />
          </div>
          <div className="lg:col-span-2">
            <IHSGComparison data={ihsgComparison} />
          </div>
        </div>

        {/* Row 3: Currency line chart — fetches its own data */}
        <CurrencyTrend />
      </div>
    </main>
  );
}
