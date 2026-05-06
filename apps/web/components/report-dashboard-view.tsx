"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Metric = {
  label: string;
  raw?: number | null;
  display?: string | null;
  compactDisplay?: string | null;
  color?: string | null;
  percentDisplay?: string | null;
};

type ReportCards = {
  inscriptions: {
    title: string;
    rnpPersonnesTotal: Metric;
    rsuMenagesTotal: Metric;
    rsuPersonnesTotal?: Metric;
    nouvellesInscriptionsMois: Metric;
    evolutionMois: Metric;
  };
  programmesSociaux: {
    title: string;
    asdMenagesActifs: Metric;
    asdPersonnesActives?: Metric;
    amoMenagesActifs: Metric;
    amoPersonnesActives?: Metric;
  };
  traitementFms: {
    title: string;
    demandesInjectees: Metric;
    demandesTraitees: Metric;
    tauxTraitementPct: Metric;
  };
  resultatFms: {
    title: string;
    douteConfirme: Metric;
    douteConfirmePct: Metric;
    douteLeve: Metric;
    douteLevePct: Metric;
  };
  radiationFraude: Record<string, Metric | string | number | null>;
  rescoring: Record<string, Metric | string | number | null>;
  economieBudgetaire: {
    title: string;
    fraude: Metric;
    rescoring: Metric;
    total: Metric;
  };
};

type RsuPoint = {
  month: string;
  label: string;
  raw: number;
  display: string;
};

type RsuTrendPoint = {
  month: string;
  raw: number;
};

type AsdPoint = {
  month: string;
  label: string;
  entrantsRaw: number;
  entrantsDisplay: string;
  sortantsRaw: number;
  sortantsDisplay: string;
  netRaw: number;
  netDisplay: string;
};

type FmsMatrixRow = {
  typeFamille: string;
  niveauRisque: string;
  demandesTraiteesRaw: number;
  douteConfirmeRaw: number;
  douteConfirmePctDisplay: string;
  douteLeveRaw: number;
  douteLevePctDisplay: string;
};

type BlockedNationalRow = {
  motifBlocage: string;
  menagesRaw: number;
  menagesDisplay: string;
};

type RegionFluxRow = {
  codeRegion: string;
  region: string;
  entrantsRaw: number;
  entrantsDisplay: string;
  sortantsRaw: number;
  sortantsDisplay: string;
  netRaw: number;
  netDisplay: string;
};

type RegionBlockedRow = {
  codeRegion: string;
  region: string;
  menagesRaw: number;
  menagesDisplay: string;
};

type TopProvinceFluxRow = {
  province: string;
  entrantsRaw: number;
  sortantsRaw: number;
  netRaw: number;
  netDisplay: string;
};

type TopProvinceBlockedRow = {
  province: string;
  menagesRaw: number;
  menagesDisplay: string;
};

export type ReportDashboard = {
  meta: {
    idChargement?: string | null;
    titreRapport?: string;
    dateRapport?: string | null;
    dateReferenceDonnees?: string | null;
    moisReportingCourant?: string | null;
    dateRange?: {
      startDate: string;
      endDate: string;
    };
  };
  cards: ReportCards;
  charts: {
    rsuInscriptionsMensuelles: {
      title: string;
      series: RsuPoint[];
      trend: RsuTrendPoint[];
    };
    asdEntreesSorties: {
      title: string;
      series: AsdPoint[];
    };
    fmsMatriceRisque: {
      title: string;
      rows: FmsMatrixRow[];
    };
    menagesBloquesNational: {
      title: string;
      rows: BlockedNationalRow[];
    };
    fluxRegionauxAsdAmot: {
      title: string;
      rows: RegionFluxRow[];
    };
    menagesBloquesRegionaux: {
      title: string;
      rows: RegionBlockedRow[];
    };
  };
  tables: {
    rsuEvolution: RsuPoint[];
    asdEvolution: AsdPoint[];
    topProvincesFlux: TopProvinceFluxRow[];
    topProvincesBloquees: TopProvinceBlockedRow[];
  };
  footnotes: string[];
  validationSummary: {
    errors: number;
    warnings: number;
    infos: number;
  };
};

const GREEN = "#006B35";
const GREEN_SOFT = "#55A873";
const RED = "#D40000";
const RED_DARK = "#B00000";
const GRAY = "#737373";
const GRID = "#E3E8E5";

export function ReportDashboardView({
  dashboard,
}: {
  dashboard: ReportDashboard;
}): React.ReactElement {
  const d = dashboard;
  const referenceDate = d.meta.dateRapport ?? d.meta.dateReferenceDonnees;
  const budget = d.cards.economieBudgetaire;

  return (
    <div className="mx-auto max-w-[1180px] bg-[#EEF0F1] pb-4 text-[#1D2A22] shadow-sm">
      <header className="flex h-12 items-center justify-between bg-[#005E2D] px-5 text-white">
        <h1 className="text-base font-bold tracking-normal">
          {d.meta.titreRapport ?? "Tableau de bord cumulatif de suivi RSU"}
        </h1>
        <span className="text-xs font-medium">{referenceDate ? formatDate(referenceDate) : ""}</span>
      </header>

      <main className="space-y-3 p-4">
        <div className="grid gap-3 lg:grid-cols-2">
          <KpiBand title={d.cards.inscriptions.title}>
            <KpiTile metric={d.cards.inscriptions.rnpPersonnesTotal} sublabel="au RNP" />
            <KpiTile metric={d.cards.inscriptions.rsuMenagesTotal} />
          </KpiBand>
          <KpiBand title={d.cards.programmesSociaux.title}>
            <KpiTile metric={d.cards.programmesSociaux.asdMenagesActifs} />
            <KpiTile metric={d.cards.programmesSociaux.amoMenagesActifs} />
          </KpiBand>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <Panel title={d.charts.rsuInscriptionsMensuelles.title}>
            <RsuChart
              points={d.charts.rsuInscriptionsMensuelles.series}
              trend={d.charts.rsuInscriptionsMensuelles.trend}
            />
            <CompactTable
              columns={[
                ["Mois", "label"],
                ["Inscrits", "display"],
                ["Evolution", "deltaDisplay"],
                ["Evol. (%)", "percentDisplay"],
              ]}
              rows={d.tables.rsuEvolution}
            />
          </Panel>

          <Panel title={d.charts.asdEntreesSorties.title}>
            <AsdChart points={d.charts.asdEntreesSorties.series} />
            <CompactTable
              columns={[
                ["Mois", "label"],
                ["Entrants", "entrantsDisplay"],
                ["Sortants", "sortantsDisplay"],
                ["Net", "netDisplay"],
              ]}
              rows={d.tables.asdEvolution}
            />
          </Panel>
        </div>

        <div className="space-y-2">
          <SectionLabel>Traitement FMS</SectionLabel>
          <div className="grid gap-3 md:grid-cols-3">
            <KpiTile metric={d.cards.traitementFms.demandesTraitees} sublabel={d.cards.traitementFms.tauxTraitementPct.display ?? ""} />
            <KpiTile metric={d.cards.resultatFms.douteConfirme} sublabel={d.cards.resultatFms.douteConfirmePct.display ?? ""} tone="red" />
            <KpiTile metric={d.cards.resultatFms.douteLeve} sublabel={d.cards.resultatFms.douteLevePct.display ?? ""} />
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <KpiBand title="Radiation pour fraude">
            <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "asdMenagesRadies")} tone="red" />
            <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "amoMenagesRadies")} tone="red" />
          </KpiBand>
          <KpiBand title="Rescoring">
            <KpiTile metric={metricFromBlock(d.cards.rescoring, "asdMenagesSortants")} tone="red" />
            <KpiTile metric={metricFromBlock(d.cards.rescoring, "amoMenagesSortants")} tone="red" />
          </KpiBand>
        </div>

        <div className="space-y-2">
          <SectionLabel>{budget.title}</SectionLabel>
          <div className="grid gap-3 md:grid-cols-3">
            <KpiTile metric={budget.fraude} tone="green" />
            <KpiTile metric={budget.rescoring} tone="green" />
            <KpiTile metric={budget.total} tone="greenSolid" />
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <Panel title={d.charts.fmsMatriceRisque.title}>
            <FmsMatrixChart rows={d.charts.fmsMatriceRisque.rows} />
          </Panel>
          <Panel title={d.charts.menagesBloquesNational.title}>
            <BlockedNationalChart rows={d.charts.menagesBloquesNational.rows} />
          </Panel>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <Panel title={d.charts.fluxRegionauxAsdAmot.title}>
            <RegionFluxChart rows={d.charts.fluxRegionauxAsdAmot.rows} />
            <CompactTable
              columns={[
                ["Province", "province"],
                ["Entr.", "entrantsRaw"],
                ["Sort.", "sortantsRaw"],
                ["Net", "netDisplay"],
              ]}
              rows={d.tables.topProvincesFlux}
              headerColor="green"
            />
          </Panel>
          <Panel title={d.charts.menagesBloquesRegionaux.title}>
            <RegionBlockedChart rows={d.charts.menagesBloquesRegionaux.rows} />
            <CompactTable
              columns={[
                ["Province", "province"],
                ["Bloqués", "menagesDisplay"],
              ]}
              rows={d.tables.topProvincesBloquees}
              headerColor="green"
            />
          </Panel>
        </div>

        {d.footnotes.length > 0 ? (
          <ol className="space-y-1 px-1 text-[11px] leading-4 text-slate-700">
            {d.footnotes.map((note, index) => (
              <li key={`${note}-${index}`}>
                {index + 1}- {note}
              </li>
            ))}
          </ol>
        ) : null}
      </main>
    </div>
  );
}

function KpiBand({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <section className="space-y-1">
      <SectionLabel>{title}</SectionLabel>
      <div className="grid gap-3 sm:grid-cols-2">{children}</div>
    </section>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <h2 className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#0D5130]">
      {children}
    </h2>
  );
}

function KpiTile({
  metric,
  sublabel,
  tone,
}: {
  metric: Metric;
  sublabel?: string;
  tone?: "green" | "greenSolid" | "red";
}): React.ReactElement {
  const isSolid = tone === "greenSolid";
  const accent = tone === "red" ? "border-l-[#D40000]" : "border-l-[#006B35]";
  const valueColor = tone === "red" ? "text-[#D40000]" : isSolid ? "text-white" : "text-[#006B35]";

  return (
    <div
      className={`min-h-[62px] border-l-4 ${accent} ${
        isSolid ? "bg-[#006B35] text-white" : "bg-white text-slate-900"
      } px-3 py-2 shadow-sm`}
    >
      <p className={`text-[21px] font-extrabold leading-6 ${valueColor}`}>
        {metric.compactDisplay ?? metric.display ?? "-"}
      </p>
      <p className={`mt-1 text-[11px] font-semibold leading-3 ${isSolid ? "text-white" : "text-slate-900"}`}>
        {metric.label}
      </p>
      {sublabel ? (
        <p className={`mt-0.5 text-[10px] ${isSolid ? "text-white/80" : "text-slate-500"}`}>
          {sublabel}
        </p>
      ) : null}
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <section className="bg-white p-3 shadow-sm">
      <h2 className="mb-2 text-[11px] font-bold text-[#102014]">{title}</h2>
      {children}
    </section>
  );
}

function RsuChart({
  points,
  trend,
}: {
  points: RsuPoint[];
  trend: RsuTrendPoint[];
}): React.ReactElement {
  const data = points.map((point) => ({
    ...point,
    value: point.raw,
    trend: trend.find((candidate) => candidate.month === point.month)?.raw ?? null,
  }));

  return (
    <div className="h-[220px]">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#475569" }} />
          <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="value" name="Inscrits RNP" fill={GREEN_SOFT} barSize={24} />
          <Line
            type="monotone"
            dataKey="trend"
            name="Tendance"
            stroke={GREEN}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function AsdChart({ points }: { points: AsdPoint[] }): React.ReactElement {
  return (
    <div className="h-[220px]">
      <ResponsiveContainer>
        <ComposedChart data={points} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#475569" }} />
          <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="netRaw" name="Delta" fill="#B8C7BD" barSize={18} />
          <Line type="monotone" dataKey="entrantsRaw" name="Entrées" stroke={GREEN} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="sortantsRaw" name="Sorties" stroke={RED} strokeWidth={2} dot={{ r: 3 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function FmsMatrixChart({ rows }: { rows: FmsMatrixRow[] }): React.ReactElement {
  const data = rows.map((row) => ({
    label: `${shorten(row.typeFamille)} ${shortRisk(row.niveauRisque)}`,
    confirme: row.douteConfirmeRaw,
    leve: row.douteLeveRaw,
  }));

  return (
    <div className="h-[310px]">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 28 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis dataKey="label" interval={0} angle={-90} textAnchor="end" tick={{ fontSize: 9, fill: "#475569" }} height={68} />
          <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="confirme" stackId="fms" name="Doute confirmé" fill={RED} />
          <Bar dataKey="leve" stackId="fms" name="Doute levé" fill={GREEN} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function BlockedNationalChart({ rows }: { rows: BlockedNationalRow[] }): React.ReactElement {
  return (
    <div className="h-[310px]">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 18, right: 12, left: 0, bottom: 12 }}>
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis dataKey="motifBlocage" tick={{ fontSize: 10, fill: "#475569" }} />
          <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Bar dataKey="menagesRaw" name="Ménages bloqués" barSize={42}>
            {rows.map((row, index) => (
              <Cell key={row.motifBlocage} fill={index === rows.length - 1 ? RED : index === 1 ? GREEN_SOFT : GREEN} />
            ))}
            <LabelList dataKey="menagesDisplay" position="top" fontSize={11} fill="#111827" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RegionFluxChart({ rows }: { rows: RegionFluxRow[] }): React.ReactElement {
  const data = rows.filter((row) => row.entrantsRaw || row.sortantsRaw);
  return (
    <div className="h-[300px]">
      <ResponsiveContainer>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 18, left: 0, bottom: 8 }}
        >
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis type="number" tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <YAxis type="category" dataKey="codeRegion" width={34} tick={{ fontSize: 10, fill: "#475569" }} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="entrantsRaw" name="Entrants" fill={GREEN} barSize={8} />
          <Bar dataKey="sortantsRaw" name="Sortants" fill={RED} barSize={8} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RegionBlockedChart({ rows }: { rows: RegionBlockedRow[] }): React.ReactElement {
  const data = [...rows]
    .filter((row) => row.menagesRaw > 0)
    .sort((a, b) => b.menagesRaw - a.menagesRaw);
  return (
    <div className="h-[300px]">
      <ResponsiveContainer>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 28, left: 0, bottom: 8 }}
        >
          <CartesianGrid stroke={GRID} strokeDasharray="2 3" />
          <XAxis type="number" tick={{ fontSize: 10, fill: "#475569" }} tickFormatter={formatCompactAxis} />
          <YAxis type="category" dataKey="codeRegion" width={34} tick={{ fontSize: 10, fill: "#475569" }} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Bar dataKey="menagesRaw" name="Bloqués" fill={RED_DARK} barSize={10}>
            <LabelList dataKey="menagesDisplay" position="right" fontSize={10} fill="#111827" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CompactTable({
  rows,
  columns,
  headerColor = "gray",
}: {
  rows: Record<string, unknown>[];
  columns: [string, string][];
  headerColor?: "green" | "gray";
}): React.ReactElement {
  return (
    <div className="mt-2 overflow-hidden border border-[#D9E0DC]">
      <table className="w-full table-fixed text-[10px]">
        <thead className={headerColor === "green" ? "bg-[#006B35] text-white" : "bg-[#F2F4F3] text-[#214331]"}>
          <tr>
            {columns.map(([label]) => (
              <th key={label} className="px-2 py-1 text-left font-bold">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#E4E8E5] bg-white">
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index}>
                {columns.map(([label, key]) => (
                  <td key={`${label}-${key}`} className="px-2 py-1 text-slate-700">
                    {formatCell(row[key])}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td className="px-2 py-2 text-slate-500" colSpan={columns.length}>
                Aucune donnée
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function metricFromBlock(
  block: Record<string, Metric | string | number | null>,
  key: string,
): Metric {
  const value = block[key];
  if (isMetric(value)) return value;
  return { label: key, display: "-" };
}

function isMetric(value: unknown): value is Metric {
  return typeof value === "object" && value !== null && "label" in value;
}

function formatCell(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "string") return value;
  return String(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(value);
}

function formatCompactAxis(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${formatNumber(value / 1_000_000)} M`;
  if (abs >= 1_000) return `${formatNumber(value / 1_000)} k`;
  return formatNumber(value);
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function shorten(value: string): string {
  return value
    .replace("Ménage ", "")
    .replace("Cas ", "")
    .replace(" artificiel ou éclaté", "")
    .slice(0, 18);
}

function shortRisk(value: string): string {
  const lower = value.toLowerCase();
  if (lower.includes("élev") || lower.includes("elev")) return "Elevé";
  if (lower.includes("moy")) return "Moyen";
  return value.slice(0, 8);
}
