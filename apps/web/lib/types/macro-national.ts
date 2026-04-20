export type InscriptionsKPIs = {
  total_menages: number;
  total_personnes: number;
  new_menages_last_month: number;
  new_menages_last_month_pct_change: number | null;
};

export type ProgrammesSociaux = {
  tadamon_beneficiaries: number;
  amo_beneficiaries: number;
};

export type MonthlyPoint = {
  month: string;
  value: number;
  delta: number | null;
  pct_change: number | null;
};

export type EntriesExitsPoint = {
  month: string;
  entrants: number;
  sortants: number;
};

export type FMSKPIs = {
  demandes_traitees: number;
  doute_confirme: number;
  doute_leve: number;
};

export type FMSBucket = {
  type_famille: string;
  niveau_risque: string;
  doute_confirme: number;
  doute_leve: number;
};

export type RadiationFraude = {
  menages_radies: number;
  personnes_radiees: number;
};

export type Rescoring = {
  menages_rescores: number;
  personnes_rescorees: number;
};

export type EconomieBudgetaire = {
  fraude: number;
  rescoring: number;
  total: number;
};

export type MenagesBloquesCategory = {
  category: string;
  count: number;
};

export type RegionFlux = {
  region: string;
  entrants: number;
  sortants: number;
};

export type RegionBloques = {
  region: string;
  bloques: number;
};

export type ProvinceRanking = {
  province: string;
  value: number;
};

export type MacroNationalPayload = {
  reporting_date: string | null;
  inscriptions_kpis: InscriptionsKPIs | null;
  programmes_sociaux: ProgrammesSociaux | null;
  monthly_evolution: MonthlyPoint[] | null;
  entries_exits: EntriesExitsPoint[] | null;
  fms_kpis: FMSKPIs | null;
  fms_buckets: FMSBucket[] | null;
  radiation_fraude: RadiationFraude | null;
  rescoring: Rescoring | null;
  economie_budgetaire: EconomieBudgetaire | null;
  menages_bloques_categories: MenagesBloquesCategory[] | null;
  region_flux: RegionFlux[] | null;
  region_bloques: RegionBloques[] | null;
  top_provinces_inscriptions: ProvinceRanking[] | null;
  top_provinces_bloques: ProvinceRanking[] | null;
};
