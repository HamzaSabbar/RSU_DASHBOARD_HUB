import { KPI_SECTIONS } from "@/lib/kpi-sections";

export const DASHBOARD_VIEWS: Record<string, string> = {
  overview: "Vue d'ensemble",
  ...KPI_SECTIONS,
};

export type DashboardViewId = keyof typeof DASHBOARD_VIEWS;

export function isDashboardViewId(value: string): value is DashboardViewId {
  return value in DASHBOARD_VIEWS;
}
