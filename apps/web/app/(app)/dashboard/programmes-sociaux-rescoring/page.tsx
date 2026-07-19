import Link from "next/link";
import { ChevronRight, Database } from "lucide-react";

import {
  SocialProgramsRescoringDashboard,
  type SocialDashboardData,
  type SocialFilterOptions,
} from "@/components/social-programs-rescoring-dashboard";
import { ApiError, apiFetch } from "@/lib/api";

export const dynamic = "force-dynamic";

type SearchParams = {
  subject?: string;
  region_id?: string;
  province_id?: string;
  start_date?: string;
  end_date?: string;
  granularity?: string;
};

export default async function ProgrammesSociauxRescoringPage({
  searchParams,
}: {
  searchParams?: SearchParams;
}): Promise<React.ReactElement> {
  const options = await getOptions();
  if (!options) return <NoPublishedData />;

  const filters = {
    subject: normalizeSubject(searchParams?.subject),
    region_id: optionalInteger(searchParams?.region_id),
    province_id: optionalInteger(searchParams?.province_id),
    start_date: validDate(searchParams?.start_date) ?? options.period_start,
    end_date: validDate(searchParams?.end_date) ?? options.period_end,
    granularity: normalizeGranularity(searchParams?.granularity),
  };
  const data = await apiFetch<SocialDashboardData>(
    "/api/boards/programmes-sociaux-rescoring/dashboard",
    { searchParams: filters },
  );

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <div className="flex items-center gap-2 text-xs text-brand-muted">
          <Link href="/dashboard" className="hover:text-brand-ink">Hub</Link>
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          <span className="font-medium text-brand-ink">Programmes sociaux / Rescoring</span>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-brand-primary">
          <Database className="h-3 w-3" aria-hidden />
          CSV publié · {options.release_key}
        </span>
      </header>
      <main className="px-5 py-5">
        <SocialProgramsRescoringDashboard options={options} data={data} />
      </main>
    </div>
  );
}

async function getOptions(): Promise<SocialFilterOptions | null> {
  try {
    return await apiFetch<SocialFilterOptions>(
      "/api/boards/programmes-sociaux-rescoring/filters",
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

function NoPublishedData(): React.ReactElement {
  return (
    <div className="min-h-screen bg-brand-bg px-5 py-5">
      <div className="rounded-md border border-brand-border bg-white p-6">
        <h1 className="text-lg font-semibold text-brand-ink">Programmes sociaux / Rescoring</h1>
        <p className="mt-2 max-w-2xl text-sm text-brand-muted">
          Aucune version analytique n’est publiée. Un administrateur doit lancer le premier import du dossier CSV RSU; le dashboard restera vide tant que la validation et la préparation DuckDB/Parquet ne sont pas terminées.
        </p>
      </div>
    </div>
  );
}

function optionalInteger(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function validDate(value: string | undefined): string | undefined {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : undefined;
}

function normalizeSubject(value: string | undefined): "ALL" | "ASD" | "AMOT" {
  return value === "ASD" || value === "AMOT" ? value : "ALL";
}

function normalizeGranularity(value: string | undefined): "day" | "week" | "month" | "quarter" {
  return value === "day" || value === "week" || value === "quarter" ? value : "month";
}
