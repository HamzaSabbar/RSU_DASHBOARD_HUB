import { notFound } from "next/navigation";
import { DashboardFilters } from "@/components/kpi/dashboard-filters";
import { ExportDownloadButton } from "@/components/export-download-button";
import { KpiPanel } from "@/components/kpi/kpi-panel";
import {
  exportPdfHref,
  getKpiFilters,
  getSection,
  readGlobalFilters,
  readKpiSpecificFilters,
  type SearchParams,
} from "@/lib/kpi-api";
import { KPI_SECTIONS } from "@/lib/kpi-sections";

export const dynamic = "force-dynamic";

export default async function SectionPage({
  params,
  searchParams,
}: {
  params: { section: string };
  searchParams: SearchParams;
}): Promise<React.ReactElement> {
  if (!(params.section in KPI_SECTIONS)) {
    notFound();
  }

  const filters = readGlobalFilters(searchParams);
  const kpiFilters = readKpiSpecificFilters(searchParams);
  const [filterOptions, section] = await Promise.all([
    getKpiFilters(),
    getSection(params.section, filters, kpiFilters),
  ]);

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <h1 className="text-sm font-semibold text-brand-ink">{section.title}</h1>
        <ExportDownloadButton
          href={exportPdfHref(params.section, filters)}
          filename={`rsu-kpi-${params.section}.pdf`}
          className="inline-flex h-8 items-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg disabled:cursor-not-allowed disabled:opacity-50"
        >
          Exporter en PDF
        </ExportDownloadButton>
      </header>

      <div className="space-y-6 px-5 py-8">
        <DashboardFilters options={filterOptions} />

        {section.cards.length === 0 ? (
          <p className="text-sm text-brand-muted">Aucun KPI dans cette section.</p>
        ) : (
          <section className="grid gap-4 xl:grid-cols-2">
            {section.cards.map((card) => (
              <KpiPanel
                key={card.code}
                card={card}
                metadata={filterOptions.per_kpi[card.code]}
              />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}
