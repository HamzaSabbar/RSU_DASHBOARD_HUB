import { notFound } from "next/navigation";
import { BrandMark } from "@/components/brand-mark";
import {
  ReportDashboardView,
  type ReportDashboard,
} from "@/components/report-dashboard-view";
import { DASHBOARD_CHARTS, isDashboardChartId } from "@/lib/dashboard-export";
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
  const range = dashboard.meta.dateRange;

  return (
    <main className="min-h-screen bg-white px-8 py-6 text-brand-ink print:p-0">
      <div className="mx-auto max-w-[1180px] space-y-5">
        <header className="flex items-start justify-between border-b border-brand-border pb-4">
          <BrandMark />
          <div className="text-right">
            <p className="text-sm font-semibold text-brand-ink">
              {chartId ? DASHBOARD_CHARTS[chartId] : "Macro National"}
            </p>
            <p className="mt-1 text-xs text-brand-muted">
              {range ? `${range.startDate} - ${range.endDate}` : "Dernière période"}
            </p>
          </div>
        </header>
        <ReportDashboardView
          dashboard={dashboard}
          mode="print"
          chartId={chartId}
        />
      </div>
    </main>
  );
}
