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

export type VBarSeries = { dataKey: string; name: string; color: string };

export function VerticalBarChart({
  data,
  labelKey,
  series,
  height = 280,
  valueFormatter = formatBigNumber,
}: {
  data: Array<Record<string, number | string>>;
  labelKey: string;
  series: VBarSeries[];
  height?: number;
  valueFormatter?: (value: number) => string;
}): React.ReactElement {
  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis dataKey={labelKey} tick={{ fontSize: 11, fill: "#64748B" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => valueFormatter(v)}
          />
          <Tooltip formatter={(v: number) => valueFormatter(v)} />
          {series.length > 1 ? <Legend wrapperStyle={{ fontSize: 12 }} /> : null}
          {series.map((s) => (
            <Bar
              key={s.dataKey}
              dataKey={s.dataKey}
              name={s.name}
              fill={s.color}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
