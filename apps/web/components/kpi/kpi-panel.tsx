import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { NoData } from "@/components/no-data";
import { MultiSeriesLineChart } from "@/components/multi-series-line-chart";
import { KpiBreakdown } from "@/components/kpi/kpi-breakdown";
import { formatBigNumber, formatPeriodLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { KpiCard as KpiCardData, KpiMetadata } from "@/lib/kpi-types";

const SERIES_PALETTE = ["#1F8A5B", "#4A4A44", "#94A3B8"];

export function formatCardValue(value: number | null, unit: string): string {
  if (value == null) return "--";
  if (unit === "%") return `${(value * 100).toFixed(1).replace(".", ",")} %`;
  if (unit === "jours") return `${value.toFixed(1).replace(".", ",")} j`;
  return formatBigNumber(value);
}

export function formatDeltaBadge(
  deltaPct: number | null,
  lowerIsBetter: boolean,
): { label: string; tone: "positive" | "danger" | "neutral" } {
  if (deltaPct == null) return { label: "", tone: "neutral" };
  const pct = deltaPct * 100;
  const improved = lowerIsBetter ? pct < 0 : pct > 0;
  const tone = pct === 0 ? "neutral" : improved ? "positive" : "danger";
  const sign = pct > 0 ? "+" : "";
  return { label: `${sign}${pct.toFixed(1).replace(".", ",")} %`, tone };
}

function seriesLabel(key: string): string {
  const labels: Record<string, string> = {
    median: "Médiane",
    p75: "P75",
    p90: "P90",
    value: "Valeur",
    rouge: "Rouge",
    orange: "Orange",
    total: "Total",
  };
  return labels[key] ?? key;
}

function periodGrainCode(grain: string): string {
  return grain === "quarter" ? "T-1" : "M-1";
}

function periodGrainTooltip(grain: string): string {
  return grain === "quarter"
    ? "Comparaison avec le trimestre précédent"
    : "Comparaison avec le mois précédent";
}

const SECONDARY_LABELS: Record<string, string> = {
  "cloturés": "Clôturés",
  en_cours: "En cours",
  otp_reussi: "OTP réussi",
  notification_recue: "Notification reçue",
};

export function KpiPanel({
  card,
  href,
  compact = false,
  metadata,
}: {
  card: KpiCardData;
  href?: string;
  compact?: boolean;
  metadata?: KpiMetadata;
}): React.ReactElement {
  const seriesKeys = Object.keys(card.windows);
  const delta = formatDeltaBadge(card.delta_pct, card.lower_is_better);
  const toneClass =
    delta.tone === "positive"
      ? "bg-emerald-50 text-brand-primary"
      : delta.tone === "danger"
        ? "bg-red-50 text-brand-danger"
        : "bg-slate-100 text-brand-muted";

  const body = (
    <Card className={cn("h-full", href && "transition hover:border-brand-border-strong")}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-brand-muted">
              {card.code}
            </p>
            <h3 className="mt-0.5 truncate text-sm font-medium text-brand-ink">{card.title}</h3>
          </div>
          {card.unavailable_reason === null && card.delta_pct != null ? (
            <span
              className={cn(
                "inline-flex shrink-0 items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold",
                toneClass,
              )}
            >
              {delta.label}
              <span
                className="font-normal opacity-70"
                title={periodGrainTooltip(card.period_grain)}
              >
                · {periodGrainCode(card.period_grain)}
              </span>
            </span>
          ) : null}
        </div>

        {!card.available ? (
          <div className="mt-4">
            <NoData label={card.unavailable_reason ?? "Données non disponibles"} />
          </div>
        ) : (
          <>
            <p className="mt-3 text-3xl font-bold tracking-tightest text-brand-dark">
              {formatCardValue(card.value, card.unit)}
            </p>

            {seriesKeys.length > 1 ? (
              <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-brand-muted">
                {seriesKeys.map((key, i) => (
                  <span key={key} className="inline-flex items-center gap-1.5">
                    <span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: SERIES_PALETTE[i % SERIES_PALETTE.length] }}
                    />
                    {seriesLabel(key)}: {formatCardValue(card.windows[key], card.unit)}
                  </span>
                ))}
              </div>
            ) : null}

            {!compact && card.trend.length > 1 ? (
              <div className="mt-4">
                <MultiSeriesLineChart
                  data={card.trend.map((p) => ({
                    ...p,
                    period: formatPeriodLabel(p.period),
                  }))}
                  xKey="period"
                  series={seriesKeys.map((key, i) => ({
                    dataKey: key,
                    name: seriesLabel(key),
                    color: SERIES_PALETTE[i % SERIES_PALETTE.length],
                  }))}
                  unit={card.unit}
                />
              </div>
            ) : null}
          </>
        )}

        {Object.keys(card.secondary_counts).length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-brand-muted">
            {Object.entries(card.secondary_counts).map(([label, value]) => (
              <span key={label}>
                {SECONDARY_LABELS[label] ?? label}:{" "}
                {value != null ? formatBigNumber(value) : "—"}
              </span>
            ))}
          </div>
        ) : null}

        {card.ignored_filters.length > 0 ? (
          <p className="mt-3 text-[11px] text-brand-muted">
            Filtre(s) non applicable(s) à ce KPI : {card.ignored_filters.join(", ")}
          </p>
        ) : null}

        {/* Independent of whether the headline value is available: a
            breakdown groups by a dimension and may resolve individual
            groups (e.g. a single source row) even when the ungrouped
            headline cannot be computed (see PERCENTILE KPIs). */}
        {!compact && metadata && metadata.breakdowns.length > 0 ? (
          <KpiBreakdown
            code={card.code}
            dimensions={metadata.breakdowns}
            defaultDimension={metadata.default_breakdown}
            initialItems={card.default_breakdown_items}
            measures={metadata.measures}
            unit={card.unit}
          />
        ) : null}
      </CardContent>
    </Card>
  );

  return href ? (
    <Link href={href} className="block h-full">
      {body}
    </Link>
  ) : (
    body
  );
}
