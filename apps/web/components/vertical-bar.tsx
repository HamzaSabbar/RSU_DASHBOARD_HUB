"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatBigNumber } from "@/lib/format";

export function VerticalBarChart({
  data,
  labelKey,
  valueKey,
  color = "#0F7B3F",
  height = 280,
}: {
  data: Array<Record<string, number | string>>;
  labelKey: string;
  valueKey: string;
  color?: string;
  height?: number;
}): React.ReactElement {
  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis dataKey={labelKey} tick={{ fontSize: 11, fill: "#64748B" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => formatBigNumber(v)}
          />
          <Tooltip formatter={(v: number) => formatBigNumber(v)} />
          <Bar dataKey={valueKey} fill={color} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
