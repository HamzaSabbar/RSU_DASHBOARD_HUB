"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBigNumber } from "@/lib/format";

export type HBarSeries = { dataKey: string; name: string; color: string };

export function HorizontalBarChart({
  data,
  labelKey,
  series,
  height = 320,
}: {
  data: Array<Record<string, number | string>>;
  labelKey: string;
  series: HBarSeries[];
  height?: number;
}): React.ReactElement {
  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 24, left: 60, bottom: 8 }}
        >
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => formatBigNumber(v)}
          />
          <YAxis
            type="category"
            dataKey={labelKey}
            tick={{ fontSize: 11, fill: "#64748B" }}
            width={140}
          />
          <Tooltip formatter={(v: number) => formatBigNumber(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s) => (
            <Bar key={s.dataKey} dataKey={s.dataKey} name={s.name} fill={s.color} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
