import { Stock, fmtNumber, fmtPct, returnColor } from "@/lib/api";

const VS_IHSG = {
  outperform:   { label: "Outperform",   bar: "bg-emerald-500", badge: "text-emerald-400 bg-emerald-400/10" },
  neutral:      { label: "Neutral",      bar: "bg-amber-500",   badge: "text-amber-400 bg-amber-400/10"    },
  underperform: { label: "Underperform", bar: "bg-red-500",     badge: "text-red-400 bg-red-400/10"        },
};

export default function StockPerformance({ data }: { data: Stock[] }) {
  const maxAbs = Math.max(...data.map((s) => Math.abs(s.return_pct)), 1);

  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-5">
      <h2 className="text-slate-400 text-xs uppercase tracking-wider mb-5">
        Stock Performance (vs IHSG)
      </h2>

      {data.length === 0 ? (
        <div className="space-y-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 bg-slate-800 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          {data.map((stock) => {
            const cfg = VS_IHSG[stock.vs_ihsg];
            const barWidth = (Math.abs(stock.return_pct) / maxAbs) * 100;

            return (
              <div key={stock.ticker}>
                {/* Row header */}
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-white text-sm font-medium">
                      {stock.ticker.replace(".JK", "")}
                    </span>
                    <span className="text-slate-500 text-xs hidden sm:inline">
                      {stock.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium tabular-nums ${returnColor(stock.return_pct)}`}>
                      {fmtPct(stock.return_pct)}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>
                </div>
                {/* Progress bar */}
                <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${cfg.bar}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                {/* Close price */}
                <p className="text-slate-500 text-xs mt-1">
                  Rp {fmtNumber(stock.close, 0)} · Vol {(stock.volume / 1_000_000).toFixed(1)}M
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
