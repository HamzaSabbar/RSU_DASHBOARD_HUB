import { apiFetch } from "@/lib/api";
import type {
  ImportRecord,
  KpiDetail,
  KpiFilterOptions,
  KpiOverviewResponse,
  KpiSectionResponse,
} from "@/lib/kpi-types";

export type GlobalFilters = {
  startDate?: string;
  endDate?: string;
  region?: string;
  province?: string;
  milieu?: string;
};

export type SearchParams = Record<string, string | string[] | undefined>;

export function readGlobalFilters(searchParams: SearchParams): GlobalFilters {
  const get = (key: string): string | undefined => {
    const v = searchParams[key];
    return Array.isArray(v) ? v[0] : v;
  };
  return {
    startDate: get("start_date"),
    endDate: get("end_date"),
    region: get("region"),
    province: get("province"),
    milieu: get("milieu"),
  };
}

/** KPI-namespaced params look like `ACC-01.age_band=18-24`. */
export function readKpiSpecificFilters(searchParams: SearchParams): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(searchParams)) {
    if (key.includes(".") && typeof value === "string") out[key] = value;
  }
  return out;
}

function globalParams(filters: GlobalFilters): Record<string, string | undefined> {
  return {
    start_date: filters.startDate,
    end_date: filters.endDate,
    region: filters.region,
    province: filters.province,
    milieu: filters.milieu,
  };
}

export async function getKpiFilters(): Promise<KpiFilterOptions> {
  return apiFetch<KpiFilterOptions>("/api/kpi/filters");
}

export async function getOverview(filters: GlobalFilters): Promise<KpiOverviewResponse> {
  return apiFetch<KpiOverviewResponse>("/api/kpi/overview", {
    searchParams: globalParams(filters),
  });
}

export async function getSection(
  section: string,
  filters: GlobalFilters,
  kpiFilters: Record<string, string> = {},
): Promise<KpiSectionResponse> {
  return apiFetch<KpiSectionResponse>(`/api/kpi/sections/${section}`, {
    searchParams: { ...globalParams(filters), ...kpiFilters },
  });
}

export async function getKpiDetail(
  code: string,
  filters: GlobalFilters,
  options: { breakdown?: string; kpiFilters?: Record<string, string> } = {},
): Promise<KpiDetail> {
  return apiFetch<KpiDetail>(`/api/kpi/${code}`, {
    searchParams: {
      ...globalParams(filters),
      ...(options.kpiFilters ?? {}),
      breakdown: options.breakdown,
    },
  });
}

export async function getImportsHistory(): Promise<{ imports: ImportRecord[] }> {
  return apiFetch<{ imports: ImportRecord[] }>("/api/kpi/imports");
}

/** Builds the href for the client-side `ExportDownloadButton`, carrying the
 * currently active global filters through to `/dashboard/kpi/print`. */
export function exportPdfHref(view: string, filters: GlobalFilters): string {
  const params = new URLSearchParams({ view });
  const entries: [string, string | undefined][] = [
    ["start_date", filters.startDate],
    ["end_date", filters.endDate],
    ["region", filters.region],
    ["province", filters.province],
    ["milieu", filters.milieu],
  ];
  for (const [key, value] of entries) {
    if (value) params.set(key, value);
  }
  return `/api/kpi/export/pdf?${params.toString()}`;
}
