export const DASHBOARD_CHARTS = {
  "rsu-inscriptions": "Inscriptions RSU / RNP",
  "asd-entrees-sorties": "Entrées et sorties ASD",
  "fms-matrice-risque": "Matrice de risque FMS",
  "menages-bloques-national": "Ménages bloqués - national",
  "flux-regionaux": "Flux régionaux",
  "menages-bloques-regionaux": "Ménages bloqués - régional",
} as const;

export type DashboardChartId = keyof typeof DASHBOARD_CHARTS;

export function isDashboardChartId(value: string): value is DashboardChartId {
  return value in DASHBOARD_CHARTS;
}
