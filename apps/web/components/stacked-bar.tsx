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
import type { FMSBucket } from "@/lib/types/macro-national";

type GroupedRow = {
  group: string;
  eleve_confirme: number;
  eleve_leve: number;
  moyen_confirme: number;
  moyen_leve: number;
};

function normalizeRisk(s: string): "eleve" | "moyen" | null {
  const t = s.toLowerCase();
  if (t.startsWith("élev") || t.startsWith("elev")) return "eleve";
  if (t.startsWith("moy")) return "moyen";
  return null;
}

export function FMSStackedBar({ buckets }: { buckets: FMSBucket[] }): React.ReactElement {
  const byFamily = new Map<string, GroupedRow>();
  for (const b of buckets) {
    const row = byFamily.get(b.type_famille) ?? {
      group: b.type_famille,
      eleve_confirme: 0,
      eleve_leve: 0,
      moyen_confirme: 0,
      moyen_leve: 0,
    };
    const r = normalizeRisk(b.niveau_risque);
    if (r === "eleve") {
      row.eleve_confirme += b.doute_confirme;
      row.eleve_leve += b.doute_leve;
    } else if (r === "moyen") {
      row.moyen_confirme += b.doute_confirme;
      row.moyen_leve += b.doute_leve;
    }
    byFamily.set(b.type_famille, row);
  }
  const data = [...byFamily.values()];

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="2 4" stroke="#E2E8F0" />
          <XAxis dataKey="group" tick={{ fontSize: 11, fill: "#64748B" }} />
          <YAxis
            tick={{ fontSize: 11, fill: "#64748B" }}
            tickFormatter={(v: number) => formatBigNumber(v)}
          />
          <Tooltip formatter={(v: number) => formatBigNumber(v)} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="eleve_confirme" stackId="eleve" name="Élevé: doute confirmé" fill="#DC2626" />
          <Bar dataKey="eleve_leve" stackId="eleve" name="Élevé: doute levé" fill="#16A34A" />
          <Bar dataKey="moyen_confirme" stackId="moyen" name="Moyen: doute confirmé" fill="#F59E0B" />
          <Bar dataKey="moyen_leve" stackId="moyen" name="Moyen: doute levé" fill="#0F7B3F" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
