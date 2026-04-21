"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBigNumber, formatMonth } from "@/lib/format";

export type LineChartPoint = {
  month: string;
  value: number;
};

export function EvolutionLineChart({
  data,
  color = "#0F7B3F",
}: {
  data: LineChartPoint[];
  color?: string;
}): React.ReactElement {
  const points = data.map((p) => ({ ...p, label: formatMonth(p.month) }));
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#64748B" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => formatBigNumber(v)}
          />
          <Tooltip
            formatter={(v: number) => formatBigNumber(v)}
            labelStyle={{ fontSize: 12 }}
            contentStyle={{ fontSize: 12 }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
