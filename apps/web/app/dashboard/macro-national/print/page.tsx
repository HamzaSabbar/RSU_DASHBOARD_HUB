import { notFound } from "next/navigation";
import {
  ReportDashboardView,
  type ReportDashboard,
} from "@/components/report-dashboard-view";
import { isDashboardChartId } from "@/lib/dashboard-export";
import { apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MacroNationalPrintPage({
  searchParams,
}: {
  searchParams?: { startDate?: string; endDate?: string; chartId?: string };
}): Promise<React.ReactElement> {
  const chartParam = searchParams?.chartId;
  if (chartParam && !isDashboardChartId(chartParam)) notFound();
  const chartId = chartParam && isDashboardChartId(chartParam) ? chartParam : undefined;

  const dashboard = await apiFetch<ReportDashboard>("/api/reports/dashboard", {
    searchParams: {
      startDate: searchParams?.startDate,
      endDate: searchParams?.endDate,
    },
  });

  return (
    <main className="report-pdf-page min-h-screen bg-[#ECEEEF] text-brand-ink">
      {chartId ? null : (
        <header className="flex h-[50px] items-center justify-between bg-brand-primary px-9 text-white">
          <h1 className="text-[22px] font-bold leading-none">
            Tableau de bord hebdomadaire de suivi RSU
          </h1>
          <p className="text-sm text-white/70">
            {formatDate(dashboard.meta.dateReferenceDonnees ?? dashboard.meta.dateRapport)}
          </p>
        </header>
      )}

      <div className={chartId ? "px-5 py-5" : "px-9 py-5"}>
        <ReportDashboardView
          dashboard={dashboard}
          mode={chartId ? "print" : "referencePdf"}
          chartId={chartId}
          canExport={false}
        />
      </div>
    </main>
  );
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(year, month - 1, day));
}
