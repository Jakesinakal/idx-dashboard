import { IHSGPoint, fmtNumber } from "@/lib/api";

const PERIOD_LABEL: Record<string, string> = {
  today: "Today",
  "30d": "30 days ago",
  "60d": "60 days ago",
  "90d": "90 days ago",
};

export default function IHSGComparison({ data }: { data: IHSGPoint[] }) {
  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-5 h-full">
      <h2 className="text-slate-400 text-xs uppercase tracking-wider mb-2">
        IHSG Comparison
      </h2>

      {data.length === 0 ? (
        <div className="space-y-4 mt-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-slate-800 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="divide-y divide-slate-800">
          {data.map((point) => {
            const isToday = point.period === "today";
            const up = point.change_pct >= 0;

            return (
              <div key={point.period} className="py-3.5 flex justify-between items-center">
                <div>
                  <p className={`text-sm font-medium ${isToday ? "text-white" : "text-slate-300"}`}>
                    {PERIOD_LABEL[point.period] ?? point.period}
                  </p>
                  <p className="text-slate-500 text-xs mt-0.5">{point.date}</p>
                </div>
                <div className="text-right">
                  <p className={`font-semibold tabular-nums ${isToday ? "text-white" : "text-slate-300"}`}>
                    {fmtNumber(point.ihsg_close)}
                  </p>
                  {!isToday && (
                    <p className={`text-xs mt-0.5 ${up ? "text-emerald-400" : "text-red-400"}`}>
                      {up ? "▲" : "▼"} {Math.abs(point.change_pct).toFixed(2)}% from today
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
