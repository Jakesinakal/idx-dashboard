import { Snapshot, fmtNumber, fmtPct, returnColor } from "@/lib/api";

function Card({
  label,
  value,
  sub,
  subColor,
}: {
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
}) {
  return (
    <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-5">
      <p className="text-slate-400 text-xs uppercase tracking-wider mb-2">{label}</p>
      <p className="text-white text-2xl font-semibold tabular-nums">{value}</p>
      {sub && <p className={`text-sm mt-1 ${subColor ?? "text-slate-400"}`}>{sub}</p>}
    </div>
  );
}

function SkeletonCard() {
  return <div className="bg-slate-900 border border-slate-700/50 rounded-xl p-5 h-[104px] animate-pulse" />;
}

export default function MarketSnapshot({ data }: { data: Snapshot | null }) {
  if (!data) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card
        label="IHSG"
        value={fmtNumber(data.ihsg_close)}
        sub={`${fmtPct(data.ihsg_return_pct)} today`}
        subColor={returnColor(data.ihsg_return_pct)}
      />
      <Card
        label="USD / IDR"
        value={fmtNumber(data.usd_idr, 0)}
      />
      <Card
        label="Fed Funds Rate"
        value={`${data.fed_rate.toFixed(2)}%`}
      />
      <Card
        label="US CPI"
        value={data.cpi_us.toFixed(1)}
      />
    </div>
  );
}
