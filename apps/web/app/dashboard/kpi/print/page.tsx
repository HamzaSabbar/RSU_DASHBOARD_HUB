import { notFound } from "next/navigation";
import { BrandMark } from "@/components/brand-mark";
import { formatCardValue, formatDeltaBadge, KpiPanel } from "@/components/kpi/kpi-panel";
import { getOverview, getSection, readGlobalFilters, type SearchParams } from "@/lib/kpi-api";
import { isDashboardViewId } from "@/lib/dashboard-export";
import { formatPeriodLabel } from "@/lib/format";
import type { KpiCard } from "@/lib/kpi-types";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

/** Unauthenticated-shaped print target used only by `lib/pdf-render.ts`'s
 * headless Chromium export -- the underlying data fetch still requires a
 * forwarded session cookie. */
export default async function KpiPrintPage({
  searchParams,
}: {
  searchParams: SearchParams;
}): Promise<React.ReactElement> {
  const viewParam = typeof searchParams.view === "string" ? searchParams.view : "overview";
  if (!isDashboardViewId(viewParam)) {
    notFound();
  }

  const filters = readGlobalFilters(searchParams);
  const { title, cards } =
    viewParam === "overview"
      ? { title: "Vue d'ensemble", cards: (await getOverview(filters)).cards }
      : await getSection(viewParam, filters);

  const now = new Date();

  return (
    <div className="kpi-print-page mx-auto p-8" data-export-ready="true">
      <header className="mb-6 flex items-center justify-between border-b border-brand-border pb-4">
        <BrandMark />
        <div className="text-right text-xs text-brand-muted">
          <p className="font-semibold text-brand-ink">{title}</p>
          <p>Exporté le {now.toLocaleDateString("fr-FR")}</p>
          {filters.startDate || filters.endDate ? (
            <p>
              Période : {filters.startDate ? formatPeriodLabel(filters.startDate) : "—"} →{" "}
              {filters.endDate ? formatPeriodLabel(filters.endDate) : "—"}
            </p>
          ) : null}
        </div>
      </header>

      <h1 className="mb-4 text-xl font-semibold text-brand-ink">
        Dashboard de pilotage des processus du RSU — {title}
      </h1>

      {viewParam === "overview" ? (
        <div className="grid grid-cols-6 gap-2">
          {cards.map((card) => (
            <OverviewPrintTile key={card.code} card={card} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {cards.map((card) => (
            <KpiPanel key={card.code} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}

/** Dense, chart-free tile so all 18 KPIs fit on a single A4 page -- the
 * full `KpiPanel` (chart + breakdown) is sized for browsing a handful of
 * KPIs on screen, not for an 18-up print grid. */
function OverviewPrintTile({ card }: { card: KpiCard }): React.ReactElement {
  const delta = formatDeltaBadge(card.delta_pct, card.lower_is_better);
  const toneClass =
    delta.tone === "positive"
      ? "text-brand-primary"
      : delta.tone === "danger"
        ? "text-brand-danger"
        : "text-brand-muted";

  return (
    <div className="rounded-md border border-brand-border p-2">
      <div className="flex items-start justify-between gap-1">
        <p className="text-[8px] font-semibold uppercase tracking-wide text-brand-muted">
          {card.code}
        </p>
        {card.available && card.delta_pct != null ? (
          <span className={cn("shrink-0 text-[9px] font-semibold", toneClass)}>
            {delta.label}
          </span>
        ) : null}
      </div>
      <p className="truncate text-[9px] leading-tight text-brand-ink" title={card.title}>
        {card.title}
      </p>
      {card.available ? (
        <p className="mt-1 text-base font-bold tracking-tightest text-brand-dark">
          {formatCardValue(card.value, card.unit)}
        </p>
      ) : (
        <p className="mt-1 text-[9px] text-brand-muted">
          {card.unavailable_reason ?? "Non disponible"}
        </p>
      )}
    </div>
  );
}
