"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { HorizontalBarChart } from "@/components/horizontal-bar";
import { VerticalBarChart } from "@/components/vertical-bar";
import { formatBigNumber } from "@/lib/format";
import type { KpiBreakdownItem, KpiDetail } from "@/lib/kpi-types";

const DIMENSION_LABELS: Record<string, string> = {
  age_band: "Tranche d'âge",
  channel: "Canal",
  gender: "Genre",
  update_type: "Type de mise à jour",
  complexity: "Standard / non standard",
  recourse_motive: "Motif du recours",
  complaint_motive: "Motif de réclamation",
  administrative_source: "Source administrative",
  flow_type: "Type de flux",
  controlled_field: "Champ contrôlé",
  incoherence_type: "Type d'incohérence",
  mail_type: "Type de courrier",
  suspicion_rule: "Règle / source de suspicion",
  suspected_fraud_type: "Type de fraude suspectée",
  region: "Région",
  province: "Province / Préfecture",
  milieu: "Milieu",
};

const MEASURE_LABELS: Record<string, string> = {
  median: "Médiane",
  p75: "P75",
  p90: "P90",
  value: "Valeur",
  rouge: "Rouge",
  orange: "Orange",
  total: "Total",
};

const SERIES_PALETTE = ["#1F8A5B", "#4A4A44", "#94A3B8"];

// Visualization choice per the number of categories in the current
// breakdown, not fixed per KPI: a handful of categories reads best as a
// vertical bar chart, a longer list as a horizontal one (labels get room to
// breathe), and anything past that as a plain table (detailed / high-
// cardinality data, e.g. dozens of provinces).
const VERTICAL_BAR_MAX_CATEGORIES = 8;
const HORIZONTAL_BAR_MAX_CATEGORIES = 20;

function measureLabel(key: string): string {
  return MEASURE_LABELS[key] ?? key;
}

function displayValue(raw: unknown, unit: string): number | null {
  if (typeof raw !== "number") return null;
  return unit === "%" ? raw * 100 : raw;
}

function chartValueFormatter(unit: string): (value: number) => string {
  return (v: number) => (unit === "%" ? `${v.toFixed(0)}%` : formatBigNumber(v));
}

export function KpiBreakdown({
  code,
  dimensions,
  defaultDimension,
  initialItems,
  measures,
  unit,
}: {
  code: string;
  dimensions: string[];
  defaultDimension: string | null;
  initialItems: KpiBreakdownItem[] | null;
  measures: string[];
  unit: string;
}): React.ReactElement | null {
  const searchParams = useSearchParams();
  const [dimension, setDimension] = useState(defaultDimension ?? dimensions[0] ?? "");
  const [items, setItems] = useState<KpiBreakdownItem[] | null>(initialItems);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!dimension) return;
    // The section endpoint already computed the default dimension's
    // breakdown server-side (see kpi/service.py compute_section) -- reuse
    // it instead of firing a redundant client fetch. This re-syncs for free
    // whenever the global/KPI filters change too, since that always causes
    // a fresh server render (and a new `initialItems`) alongside a
    // `searchParams` change that re-triggers this effect.
    if (dimension === defaultDimension && initialItems != null) {
      setItems(initialItems);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.set("breakdown", dimension);
    setLoading(true);
    fetch(`/api/kpi/detail/${code}?${params.toString()}`, { cache: "no-store" })
      .then((res) => (res.ok ? (res.json() as Promise<KpiDetail>) : null))
      .then((detail) => setItems(detail?.breakdown?.items ?? []))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, dimension, searchParams.toString()]);

  if (dimensions.length === 0) return null;

  const count = items?.length ?? 0;
  const formatter = chartValueFormatter(unit);
  const series = measures.map((m, i) => ({
    dataKey: m,
    name: measureLabel(m),
    color: SERIES_PALETTE[i % SERIES_PALETTE.length],
  }));
  const chartData = (items ?? []).map((item) => {
    const row: Record<string, number | string> = { key: String(item.key) };
    for (const m of measures) {
      row[m] = displayValue(item[m], unit) ?? 0;
    }
    return row;
  });

  return (
    <div className="mt-4 border-t border-brand-border pt-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-muted">
          Ventiler par
        </p>
        {dimensions.length > 1 ? (
          <select
            value={dimension}
            onChange={(e) => setDimension(e.target.value)}
            className="h-8 rounded-md border border-brand-border bg-white px-2 text-xs text-brand-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
          >
            {dimensions.map((d) => (
              <option key={d} value={d}>
                {DIMENSION_LABELS[d] ?? d}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-brand-muted">
            {DIMENSION_LABELS[dimension] ?? dimension}
          </span>
        )}
      </div>
      <div className="mt-2">
        {loading ? (
          <p className="text-xs text-brand-muted">Chargement...</p>
        ) : !items || count === 0 ? (
          <p className="text-xs text-brand-muted">Aucune donnée pour cette répartition.</p>
        ) : count <= VERTICAL_BAR_MAX_CATEGORIES ? (
          <VerticalBarChart
            data={chartData}
            labelKey="key"
            series={series}
            height={220}
            valueFormatter={formatter}
          />
        ) : count <= HORIZONTAL_BAR_MAX_CATEGORIES ? (
          <HorizontalBarChart
            data={chartData}
            labelKey="key"
            series={series}
            height={Math.max(240, count * 26)}
            valueFormatter={formatter}
          />
        ) : (
          <BreakdownTable items={items} measures={measures} unit={unit} />
        )}
      </div>
    </div>
  );
}

function BreakdownTable({
  items,
  measures,
  unit,
}: {
  items: KpiBreakdownItem[];
  measures: string[];
  unit: string;
}): React.ReactElement {
  return (
    <div className="max-h-80 overflow-auto rounded-md border border-brand-border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wider text-brand-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Valeur</th>
            {measures.map((m) => (
              <th key={m} className="px-3 py-2 text-right font-medium">
                {measureLabel(m)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-border">
          {items.map((item) => {
            const unavailable = item.available === false;
            return (
              <tr key={String(item.key)}>
                <td className="px-3 py-2">{String(item.key)}</td>
                {measures.map((m) => {
                  const value = displayValue(item[m], unit);
                  return (
                    <td
                      key={m}
                      className="px-3 py-2 text-right font-mono tabular-nums text-brand-ink"
                    >
                      {unavailable || value == null
                        ? "—"
                        : unit === "%"
                          ? `${value.toFixed(1).replace(".", ",")} %`
                          : formatBigNumber(value)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
