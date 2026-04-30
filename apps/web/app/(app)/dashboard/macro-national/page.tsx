import Link from "next/link";
import { BookOpen } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import {
  ReportDashboardView,
  type ReportDashboard,
} from "@/components/report-dashboard-view";
import {
  ReportDateFilter,
  type ReportAvailablePeriods,
} from "@/components/report-date-filter";
import { UploadDrawer } from "@/components/upload-drawer";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const dynamic = "force-dynamic";

export default async function MacroNationalPage({
  searchParams,
}: {
  searchParams?: { startDate?: string; endDate?: string };
}): Promise<React.ReactElement> {
  const periods = await getAvailablePeriods();
  const dashboard = await getDashboard(
    searchParams?.startDate,
    searchParams?.endDate,
  );

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-brand-dark">
            Macro National
          </h1>
          <p className="mt-1 text-sm text-brand-muted">
            Données cumulées depuis les classeurs Excel RSU validés. Le filtre
            applique un intervalle de dates aux faits actifs.
          </p>
        </div>
        <div className="flex flex-wrap items-start justify-end gap-3">
          <Link
            href="/dashboard/macro-national/kpi-methodology"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-brand-border bg-white px-3 text-sm font-medium text-slate-900 hover:bg-slate-50"
          >
            <BookOpen className="h-4 w-4" aria-hidden />
            Méthodologie KPI
          </Link>
          <ReportDateFilter
            periods={periods}
            selectedStartDate={searchParams?.startDate}
            selectedEndDate={searchParams?.endDate}
          />
          <UploadDrawer />
        </div>
      </header>

      {dashboard ? (
        <ReportDashboardView dashboard={dashboard} />
      ) : periods ? (
        <Card>
          <CardHeader>
            <CardTitle>Aucune donnée disponible pour le moment</CardTitle>
            <CardDescription>
              Aucun dashboard n’est disponible pour la période sélectionnée.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-brand-muted">
            Modifiez la date ou revenez à la dernière période disponible.
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Aucun rapport traité</CardTitle>
            <CardDescription>
              Chargez un classeur hebdomadaire RSU pour créer le premier job.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-brand-muted">
            Le dashboard apparaîtra ici dès que le worker aura terminé la
            validation et le calcul des indicateurs.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

async function getDashboard(
  startDate?: string,
  endDate?: string,
): Promise<ReportDashboard | null> {
  try {
    return await apiFetch<ReportDashboard>("/api/reports/dashboard", {
      searchParams: { startDate, endDate },
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

async function getAvailablePeriods(): Promise<ReportAvailablePeriods | null> {
  try {
    return await apiFetch<ReportAvailablePeriods>("/api/reports/available-periods");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
