"use client";

import { useSyncExternalStore } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmt, fmtInt } from "@/lib/format";
import type { IhsgPoint } from "@/lib/types";

const emptySubscribe = () => () => {};

export function IhsgChart({ series }: { series: IhsgPoint[] }) {
  // Render only on the client: ResponsiveContainer needs a measured parent,
  // which doesn't exist during server prerender. The parent reserves the
  // height, so there's no layout shift.
  const isClient = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  if (!isClient) return <div className="h-full w-full" />;

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={series} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="ihsgFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.28} />
            <stop offset="100%" stopColor="#a78bfa" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fill: "#52525b", fontSize: 11, fontFamily: "ui-monospace, monospace" }}
          tickLine={false}
          axisLine={{ stroke: "#27272a" }}
          minTickGap={48}
        />
        <YAxis
          domain={["dataMin - 40", "dataMax + 40"]}
          tick={{ fill: "#52525b", fontSize: 11, fontFamily: "ui-monospace, monospace" }}
          tickLine={false}
          axisLine={false}
          width={48}
          tickFormatter={(v: number) => fmtInt(v)}
        />
        <Tooltip
          contentStyle={{
            background: "#18181b",
            border: "1px solid #3f3f46",
            borderRadius: 8,
            fontFamily: "ui-monospace, monospace",
            fontSize: 12,
          }}
          labelStyle={{ color: "#a1a1aa" }}
          itemStyle={{ color: "#f4f4f5" }}
          formatter={(v) => [fmt(Number(v)), "IHSG"] as [string, string]}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke="#a78bfa"
          strokeWidth={2}
          fill="url(#ihsgFill)"
          dot={false}
          isAnimationActive={false}
          activeDot={{ r: 4, fill: "#a78bfa", stroke: "#09090b", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
