// Mirrors the FastAPI /api/kpi/* response shapes (kpi/service.py KpiCard,
// kpi/importer.py ImportPreview) field-for-field, snake_case included.

export type KpiTrendPoint = {
  period: string; // ISO date "YYYY-MM-DD"
} & Record<string, string | number | null>;

export type KpiCard = {
  code: string;
  title: string;
  section: string;
  unit: string;
  lower_is_better: boolean;
  value: number | null;
  windows: Record<string, number | null>;
  previous_value: number | null;
  delta_abs: number | null;
  delta_pct: number | null;
  trend: KpiTrendPoint[];
  available: boolean;
  unavailable_reason: string | null;
  applied_filters: Record<string, unknown>;
  ignored_filters: string[];
  // This KPI's reporting cadence -- drives the delta badge's "vs mois
  // précédent" / "vs trimestre précédent" label.
  period_grain: "month" | "quarter";
  // Secondary counts that don't share `windows`'s unit (e.g. REC-04's
  // headline is a delay in days, but "en cours"/"clôturés" are raw counts).
  // Empty for every KPI without `extra_measures` on the backend.
  secondary_counts: Record<string, number | null>;
  // Precomputed server-side by /api/kpi/sections/{section} so the initial
  // "Ventiler par" view never needs its own client-side fetch.
  default_breakdown_dimension: string | null;
  default_breakdown_items: KpiBreakdownItem[] | null;
};

export type KpiBreakdownItem = {
  key: string;
  /** Present (and `false`) only for PERCENTILE-kind breakdowns (INS-02,
   * MAJ-01) when a group spans more than one source row -- median/P75/P90
   * are never averaged across rows, so that group is unavailable rather
   * than showing a fabricated value. */
  available?: boolean;
} & Record<string, string | number | boolean | null | undefined>;

export type KpiDetail = {
  kpi: KpiCard;
  breakdown?: {
    dimension: string;
    items: KpiBreakdownItem[];
  };
};

export type KpiOverviewResponse = { cards: KpiCard[] };
export type KpiSectionResponse = { section: string; title: string; cards: KpiCard[] };

/** Per-KPI metadata declared explicitly in the backend registry
 * (kpi/registry.py KpiSpec) -- never a fixed set imposed across all 18 KPIs.
 * `filters` holds the distinct values seen for each KPI-specific filter
 * dimension; `breakdowns` is the ordered allowlist of dimensions this KPI
 * can be grouped ("ventilé") by, which is a distinct concept from filters
 * (a filter restricts the population, a breakdown groups it). */
export type KpiMetadata = {
  filters: Record<string, string[]>;
  breakdowns: string[];
  default_breakdown: string | null;
  measures: string[];
  time_dimension: string;
};

export type KpiFilterOptions = {
  regions: string[];
  provinces_by_region: Record<string, string[]>;
  milieux: string[];
  period: { min: string | null; max: string | null };
  sections: Record<string, string>;
  per_kpi: Record<string, KpiMetadata>;
};

export type ValidationIssue = {
  severity: "error" | "warning";
  sheet: string;
  row: number | null;
  column: string | null;
  code: string;
  message: string;
};

export type TablePreview = {
  table_key: string;
  sheet_name: string;
  rows_read: number;
  new: number;
  updated: number;
  unchanged: number;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
};

export type ImportPreview = {
  valid: boolean;
  filename: string;
  checksum: string;
  mode: "baseline" | "incremental";
  recognized_sheets: string[];
  missing_sheets: string[];
  unknown_sheets: string[];
  period_min: string | null;
  period_max: string | null;
  rows_read: number;
  rows_new: number;
  rows_updated: number;
  rows_unchanged: number;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  duplicate_of_import_id: string | null;
  already_committed: boolean;
  per_kpi: Record<string, TablePreview[]>;
};

export type ImportRecord = {
  id: string;
  filename: string;
  checksum: string;
  uploaded_at: string;
  mode: string;
  status: string;
  recognized_sheets: string[];
  missing_sheets: string[];
  unknown_sheets: string[];
  row_counts: Record<string, { new: number; updated: number; unchanged: number }>;
  period_min: string | null;
  period_max: string | null;
  committed_at: string | null;
};
