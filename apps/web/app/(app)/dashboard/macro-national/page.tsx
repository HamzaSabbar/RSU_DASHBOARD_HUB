import Link from "next/link";
import { BookOpen, ChevronRight, Download, FileSpreadsheet } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import { canManageReports } from "@/lib/roles";
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
  const session = await auth();
  const role = (session?.user as { role?: string } | undefined)?.role;
  const canManage = canManageReports(role);
  const exportQuery = buildExportQuery(
    searchParams?.startDate,
    searchParams?.endDate,
  );
  const latestBatch = latestUploadBatch(periods);

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <div className="flex items-center gap-2 text-xs text-brand-muted">
          <Link href="/dashboard" className="hover:text-brand-ink">
            Hub
          </Link>
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          <span className="font-medium text-brand-ink">Macro National</span>
        </div>
        {canManage ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link
              href="/dashboard/macro-national/kpi-methodology"
              className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg"
            >
              <BookOpen className="h-3.5 w-3.5" aria-hidden />
              Méthodologie
            </Link>
            <a
              href="/api/reports/template.xlsx"
              className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg"
            >
              <FileSpreadsheet className="h-3.5 w-3.5" aria-hidden />
              Modèle Excel
            </a>
            <a
              href={`/api/reports/dashboard/export.pdf${exportQuery}`}
              download="rsu-dashboard-macro-national.pdf"
              className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg"
            >
              <Download className="h-3.5 w-3.5" aria-hidden />
              Exporter
            </a>
            <UploadDrawer />
          </div>
        ) : null}
      </header>

      <div className="space-y-5 px-5 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-semibold text-brand-ink">
                Macro National
              </h1>
              {dashboard ? (
                <span className="rounded bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-brand-primary">
                  Données à jour
                </span>
              ) : null}
              {periods?.latestReportDate ? (
                <span className="text-xs text-brand-muted">
                  Arrêté au {formatDate(periods.latestReportDate)}
                </span>
              ) : null}
            </div>
            <p className="mt-1 max-w-2xl text-xs text-brand-muted">
              Inscriptions, programmes sociaux, traitement FMS et synthèses
              régionales issus des classeurs RSU validés.
            </p>
            {latestBatch ? (
              <div className="mt-3 inline-flex max-w-full items-center gap-2 rounded-md border border-brand-border bg-white px-3 py-2 text-xs text-brand-soft shadow-[0_1px_2px_rgba(20,20,15,0.04)]">
                <FileSpreadsheet
                  className="h-3.5 w-3.5 shrink-0 text-brand-primary"
                  aria-hidden
                />
                <span className="min-w-0 truncate">
                  Dernier fichier validé:{" "}
                  <span className="font-semibold text-brand-ink">
                    {latestBatch.originalFilename ?? latestBatch.idChargement}
                  </span>{" "}
                  ·{" "}
                  {formatRange(latestBatch.debutPeriode, latestBatch.finPeriode)}{" "}
                  · importé le {formatDateTime(latestBatch.createdAt)}
                </span>
              </div>
            ) : null}
          </div>
          <div className="flex w-full flex-wrap items-start justify-end gap-3 lg:w-auto">
            <ReportDateFilter
              periods={periods}
              selectedStartDate={searchParams?.startDate}
              selectedEndDate={searchParams?.endDate}
            />
          </div>
        </div>

        {dashboard ? (
          <ReportDashboardView dashboard={dashboard} canExport={canManage} />
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
                Chargez un classeur quotidien RSU pour créer le premier job.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-brand-muted">
              Le dashboard apparaîtra ici dès que le worker aura terminé la
              validation et le calcul des indicateurs.
            </CardContent>
          </Card>
        )}
      </div>
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

function buildExportQuery(startDate?: string, endDate?: string): string {
  const params = new URLSearchParams();
  if (startDate) params.set("startDate", startDate);
  if (endDate) params.set("endDate", endDate);
  const query = params.toString();
  return query ? `?${query}` : "";
}

function latestUploadBatch(periods: ReportAvailablePeriods | null) {
  if (!periods?.activeUploadBatches.length) return null;
  return periods.activeUploadBatches.reduce((latest, batch) =>
    batch.createdAt > latest.createdAt ? batch : latest,
  );
}

function formatRange(startDate: string | null, endDate: string | null): string {
  if (startDate && endDate && startDate !== endDate) {
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
  }
  return formatDate(endDate ?? startDate);
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

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
