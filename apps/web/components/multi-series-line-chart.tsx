"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBigNumber } from "@/lib/format";

export type MultiSeriesSpec = { dataKey: string; name: string; color: string };

function formatValue(value: number, unit: string): string {
  if (unit === "%") return `${(value * 100).toFixed(0)}%`;
  return formatBigNumber(value);
}

export function MultiSeriesLineChart({
  data,
  xKey,
  series,
  height = 256,
  unit = "",
}: {
  data: Array<Record<string, number | string | null>>;
  xKey: string;
  series: MultiSeriesSpec[];
  height?: number;
  unit?: string;
}): React.ReactElement {
  const valueFormatter = (v: number) => formatValue(v, unit);
  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: "#64748B" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => valueFormatter(v)}
            width={48}
          />
          <Tooltip
            formatter={(v: number) => (v == null ? "--" : valueFormatter(v))}
            labelStyle={{ fontSize: 12 }}
            contentStyle={{ fontSize: 12 }}
          />
          {series.length > 1 ? <Legend wrapperStyle={{ fontSize: 12 }} /> : null}
          {series.map((s) => (
            <Line
              key={s.dataKey}
              type="monotone"
              dataKey={s.dataKey}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              dot={{ r: 2.5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
