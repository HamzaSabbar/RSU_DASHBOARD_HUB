import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { DashboardFilters } from "@/components/kpi/dashboard-filters";
import { KpiPanel } from "@/components/kpi/kpi-panel";
import {
  getKpiDetail,
  getKpiFilters,
  readGlobalFilters,
  readKpiSpecificFilters,
  type SearchParams,
} from "@/lib/kpi-api";
import { KPI_SECTIONS } from "@/lib/kpi-sections";

export const dynamic = "force-dynamic";

export default async function KpiDetailPage({
  params,
  searchParams,
}: {
  params: { section: string; code: string };
  searchParams: SearchParams;
}): Promise<React.ReactElement> {
  if (!(params.section in KPI_SECTIONS)) {
    notFound();
  }

  const filters = readGlobalFilters(searchParams);
  const kpiFilters = readKpiSpecificFilters(searchParams);
  const filterOptions = await getKpiFilters();
  const metadata = filterOptions.per_kpi[params.code];
  if (!metadata) {
    notFound();
  }

  const detail = await getKpiDetail(params.code, filters, {
    breakdown: metadata.default_breakdown ?? undefined,
    kpiFilters,
  });

  if (detail.kpi.section !== params.section) {
    notFound();
  }

  const card = {
    ...detail.kpi,
    default_breakdown_dimension: metadata.default_breakdown,
    default_breakdown_items: detail.breakdown?.items ?? null,
  };

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center gap-3 border-b border-brand-border bg-brand-surface px-5">
        <Link
          href={`/dashboard/${params.section}`}
          className="inline-flex h-8 items-center gap-1.5 rounded-md px-2 text-xs font-medium text-brand-muted hover:bg-brand-bg hover:text-brand-ink"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {KPI_SECTIONS[params.section]}
        </Link>
        <h1 className="text-sm font-semibold text-brand-ink">{card.title}</h1>
      </header>

      <div className="space-y-6 px-5 py-8">
        <DashboardFilters options={filterOptions} />

        <section className="mx-auto max-w-4xl">
          <KpiPanel card={card} metadata={metadata} />
        </section>
      </div>
    </div>
  );
}
