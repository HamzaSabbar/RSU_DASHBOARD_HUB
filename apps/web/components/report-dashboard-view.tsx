"use client";

import { Download } from "lucide-react";
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
import type { DashboardChartId } from "@/lib/dashboard-export";

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
    rsuPersonnesCouvertes?: Metric;
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
      unit?: string;
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

const GREEN = "#00612F";
const GREEN_DARK = "#00572B";
const GREEN_SOFT = "#AFC7B2";
const RED = "#D40000";
const RED_DARK = "#C90000";
const GRAY = "#7B8190";
const GRID = "#E6E8EA";

export function ReportDashboardView({
  dashboard,
  mode = "interactive",
  chartId,
  canExport = true,
}: {
  dashboard: ReportDashboard;
  mode?: "interactive" | "print" | "referencePdf";
  chartId?: DashboardChartId;
  canExport?: boolean;
}): React.ReactElement {
  const d = dashboard;
  const budget = d.cards.economieBudgetaire;
  const isReferencePdf = mode === "referencePdf";
  const isPrint = mode === "print" || isReferencePdf;
  const exportQuery = dashboardDateQuery(d);

  if (chartId) {
    return (
      <div
        className="mx-auto max-w-[1080px] bg-white text-brand-ink"
        data-chart-export-target="true"
        data-export-ready="true"
      >
        {renderSingleChart(chartId, d)}
      </div>
    );
  }

  return (
    <ReferencePdfDashboard
      d={d}
      canExport={canExport && !isPrint}
      exportQuery={exportQuery}
      className={
        isReferencePdf
          ? "pdf-reference mx-auto max-w-[1040px] space-y-3 text-brand-ink"
          : "pdf-reference mx-auto max-w-[1180px] space-y-4 text-brand-ink"
      }
    />
  );

  return (
    <div
      className={
        isReferencePdf
          ? "pdf-reference mx-auto max-w-[1040px] space-y-3 text-brand-ink"
          : "mx-auto max-w-[1180px] space-y-5 text-brand-ink"
      }
      data-export-ready="true"
    >
      <section className="grid gap-5 xl:grid-cols-2">
        <div className="space-y-2">
          <SectionLabel>{d.cards.inscriptions.title}</SectionLabel>
          <div className="grid gap-3 md:grid-cols-2">
            <KeyMetricCard metric={d.cards.inscriptions.rnpPersonnesTotal} sublabel="au RNP" />
            <KeyMetricCard
              metric={d.cards.inscriptions.rsuMenagesTotal}
              sublabel={registrationPersonSublabel(
                "au RSU",
                d.cards.inscriptions.rsuPersonnesCouvertes,
              )}
            />
          </div>
        </div>

        <div className="space-y-2">
          <SectionLabel>{d.cards.programmesSociaux.title}</SectionLabel>
          <div className="grid gap-3 md:grid-cols-2">
            <KeyMetricCard
              metric={d.cards.programmesSociaux.asdMenagesActifs}
              sublabel={personSublabel(d.cards.programmesSociaux.asdPersonnesActives)}
            />
            <KeyMetricCard
              metric={d.cards.programmesSociaux.amoMenagesActifs}
              sublabel={personSublabel(d.cards.programmesSociaux.amoPersonnesActives)}
            />
          </div>
        </div>
      </section>

      <div className="grid gap-3 xl:grid-cols-2">
        <Panel
          title={d.charts.rsuInscriptionsMensuelles.title}
          subtitle={`RSU - ${unitLabel(d.charts.rsuInscriptionsMensuelles.unit)}`}
          exportChartId="rsu-inscriptions"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={isPrint}
        >
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

        <Panel
          title={d.charts.asdEntreesSorties.title}
          subtitle="Section 20. ASD - ménages"
          exportChartId="asd-entrees-sorties"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={isPrint}
        >
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

      <section className="space-y-2">
        <SectionLabel>Système de gestion de la fraude</SectionLabel>
        <p className="text-xs text-brand-muted">Demandes traitées - matrice de risque.</p>
        <div className="grid gap-3 md:grid-cols-3">
          <KpiTile
            metric={d.cards.traitementFms.demandesTraitees}
            sublabel={d.cards.traitementFms.tauxTraitementPct.display ?? ""}
          />
          <KpiTile
            metric={d.cards.resultatFms.douteConfirme}
            sublabel={d.cards.resultatFms.douteConfirmePct.display ?? ""}
            tone="red"
          />
          <KpiTile
            metric={d.cards.resultatFms.douteLeve}
            sublabel={d.cards.resultatFms.douteLevePct.display ?? ""}
          />
        </div>
      </section>

      <div className="grid gap-3 xl:grid-cols-2">
        <Panel
          title={d.charts.fmsMatriceRisque.title}
          subtitle="Famille - niveau de risque"
          exportChartId="fms-matrice-risque"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={isPrint}
        >
            <FmsMatrixChart rows={d.charts.fmsMatriceRisque.rows} />
        </Panel>
        <Panel
          title={d.charts.menagesBloquesNational.title}
          subtitle="Stock courant par motif"
          exportChartId="menages-bloques-national"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={isPrint}
        >
            <BlockedNationalChart rows={d.charts.menagesBloquesNational.rows} />
        </Panel>
      </div>

      <section className="space-y-2">
        <SectionLabel>{budget.title}</SectionLabel>
        <p className="text-xs text-brand-muted">Flux ASD / AMO et stock bloqué par région.</p>
        <div className="grid gap-3 md:grid-cols-3">
          <KpiTile metric={budget.fraude} tone="green" />
          <KpiTile metric={budget.rescoring} tone="green" />
          <KpiTile metric={budget.total} tone="greenSolid" />
        </div>
      </section>

      <section className="space-y-2">
        <SectionLabel>Radiation et rescoring</SectionLabel>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "asdMenagesRadies")} tone="red" />
          <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "amoMenagesRadies")} tone="red" />
          <KpiTile metric={metricFromBlock(d.cards.rescoring, "asdMenagesSortants")} tone="red" />
          <KpiTile metric={metricFromBlock(d.cards.rescoring, "amoMenagesSortants")} tone="red" />
        </div>
      </section>

      <section className="space-y-2">
        <SectionLabel>Découpage régional</SectionLabel>
        <div className="grid gap-3 xl:grid-cols-2">
          <Panel
            title={d.charts.fluxRegionauxAsdAmot.title}
            subtitle="T1 régions"
            exportChartId="flux-regionaux"
            exportQuery={exportQuery}
            canExport={canExport}
            isPrint={isPrint}
          >
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
          <Panel
            title={d.charts.menagesBloquesRegionaux.title}
            subtitle="Stock courant"
            exportChartId="menages-bloques-regionaux"
            exportQuery={exportQuery}
            canExport={canExport}
            isPrint={isPrint}
          >
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
      </section>

      {d.footnotes.length > 0 ? (
        <ol className="border border-brand-border bg-white px-4 py-3 text-[11px] leading-4 text-brand-muted">
          {d.footnotes.map((note, index) => (
            <li key={`${note}-${index}`}>
              {index + 1}- {note}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function ReferencePdfDashboard({
  d,
  canExport = false,
  exportQuery = "",
  className = "pdf-reference mx-auto max-w-[1040px] space-y-3 text-brand-ink",
}: {
  d: ReportDashboard;
  canExport?: boolean;
  exportQuery?: string;
  className?: string;
}): React.ReactElement {
  const budget = d.cards.economieBudgetaire;

  return (
    <div
      className={className}
      data-export-ready="true"
    >
      <section className="grid grid-cols-2 gap-5">
        <div className="space-y-2">
          <SectionLabel>{d.cards.inscriptions.title}</SectionLabel>
          <div className="grid grid-cols-2 gap-4">
            <KeyMetricCard metric={d.cards.inscriptions.rnpPersonnesTotal} sublabel="au RNP" />
            <KeyMetricCard
              metric={d.cards.inscriptions.rsuMenagesTotal}
              sublabel={registrationPersonSublabel(
                "au RSU",
                d.cards.inscriptions.rsuPersonnesCouvertes,
              )}
            />
          </div>
        </div>
        <div className="space-y-2">
          <SectionLabel>{d.cards.programmesSociaux.title}</SectionLabel>
          <div className="grid grid-cols-2 gap-4">
            <KeyMetricCard
              metric={d.cards.programmesSociaux.asdMenagesActifs}
              sublabel={personSublabel(d.cards.programmesSociaux.asdPersonnesActives)}
            />
            <KeyMetricCard
              metric={d.cards.programmesSociaux.amoMenagesActifs}
              sublabel={personSublabel(d.cards.programmesSociaux.amoPersonnesActives)}
            />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-5">
        <Panel
          title={d.charts.rsuInscriptionsMensuelles.title}
          exportChartId="rsu-inscriptions"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
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
            rows={d.tables.rsuEvolution.slice(0, 2)}
          />
        </Panel>
        <Panel
          title={d.charts.asdEntreesSorties.title}
          exportChartId="asd-entrees-sorties"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
          <AsdChart points={d.charts.asdEntreesSorties.series} />
          <CompactTable
            columns={[
              ["Mois", "label"],
              ["Entrants", "entrantsDisplay"],
              ["Sortants", "sortantsDisplay"],
              ["Net", "netDisplay"],
            ]}
            rows={d.tables.asdEvolution.slice(0, 2)}
          />
        </Panel>
      </div>

      <section className="grid grid-cols-2 gap-5">
        <div className="space-y-2">
          <SectionLabel>Traitement FMS</SectionLabel>
          <KpiTile
            metric={d.cards.traitementFms.demandesTraitees}
            sublabel={traitementFmsSublabel(d)}
          />
        </div>
        <div className="space-y-2">
          <SectionLabel>Résultat</SectionLabel>
          <div className="grid grid-cols-2 gap-4">
            <KpiTile
              metric={d.cards.resultatFms.douteConfirme}
              sublabel={resultatFmsSublabel(d.cards.resultatFms.douteConfirmePct)}
              tone="red"
            />
            <KpiTile
              metric={d.cards.resultatFms.douteLeve}
              sublabel={resultatFmsSublabel(d.cards.resultatFms.douteLevePct)}
            />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-5">
        <div className="space-y-2">
          <SectionLabel>Radiation pour fraude</SectionLabel>
          <div className="grid grid-cols-2 gap-4">
            <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "asdMenagesRadies")} tone="red" />
            <KpiTile metric={metricFromBlock(d.cards.radiationFraude, "amoMenagesRadies")} tone="red" />
          </div>
        </div>
        <div className="space-y-2">
          <SectionLabel>Rescoring</SectionLabel>
          <div className="grid grid-cols-2 gap-4">
            <KpiTile metric={metricFromBlock(d.cards.rescoring, "asdMenagesSortants")} tone="red" />
            <KpiTile metric={metricFromBlock(d.cards.rescoring, "amoMenagesSortants")} tone="red" />
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <SectionLabel>{budget.title}</SectionLabel>
        <div className="grid grid-cols-[1fr_1fr_1fr] gap-4">
          <KpiTile metric={budget.fraude} />
          <KpiTile metric={budget.rescoring} />
          <KpiTile metric={budget.total} tone="greenSolid" />
        </div>
      </section>

      <div className="grid grid-cols-2 gap-5">
        <Panel
          title={d.charts.fmsMatriceRisque.title}
          exportChartId="fms-matrice-risque"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
          <FmsMatrixChart rows={d.charts.fmsMatriceRisque.rows} />
        </Panel>
        <Panel
          title={d.charts.menagesBloquesNational.title}
          exportChartId="menages-bloques-national"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
          <BlockedNationalChart rows={d.charts.menagesBloquesNational.rows} />
        </Panel>
      </div>

      <div className="grid grid-cols-2 gap-5">
        <Panel
          title={d.charts.fluxRegionauxAsdAmot.title}
          exportChartId="flux-regionaux"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
          <RegionFluxChart rows={d.charts.fluxRegionauxAsdAmot.rows} />
          <CompactTable
            columns={[
              ["Province", "province"],
              ["Ent.", "entrantsRaw"],
              ["Sort.", "sortantsRaw"],
              ["Net", "netDisplay"],
            ]}
            rows={d.tables.topProvincesFlux.slice(0, 5)}
            headerColor="green"
          />
        </Panel>
        <Panel
          title={d.charts.menagesBloquesRegionaux.title}
          exportChartId="menages-bloques-regionaux"
          exportQuery={exportQuery}
          canExport={canExport}
          isPrint={!canExport}
        >
          <RegionBlockedChart rows={d.charts.menagesBloquesRegionaux.rows} />
          <CompactTable
            columns={[
              ["Province", "province"],
              ["Bloqués", "menagesDisplay"],
            ]}
            rows={d.tables.topProvincesBloquees.slice(0, 5)}
            headerColor="green"
          />
        </Panel>
      </div>

      {d.footnotes.length > 0 ? (
        <ol className="pdf-footnotes text-[10px] leading-4 text-brand-soft">
          {d.footnotes.map((note, index) => (
            <li key={`${note}-${index}`}>
              {index + 1}- {note}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }): React.ReactElement {
  return (
    <h2 className="section-label text-[11px] font-semibold uppercase tracking-[0.14em] text-brand-primary">
      {children}
    </h2>
  );
}

function KeyMetricCard({
  metric,
  sublabel,
}: {
  metric: Metric;
  sublabel?: string;
}): React.ReactElement {
  return (
    <div className="key-metric-card relative min-h-[154px] border border-brand-border bg-brand-surface py-6 pl-8 pr-6 shadow-card">
      <span className="absolute left-0 top-2 h-[calc(100%-16px)] w-3 bg-brand-primary" />
      <p className="key-metric-value text-4xl font-semibold leading-none tracking-normal text-brand-primary">
        {metric.compactDisplay ?? metric.display ?? "-"}
      </p>
      <p className="key-metric-label mt-2 text-xl font-semibold leading-6 text-brand-ink">
        {metric.label}
      </p>
      {sublabel ? (
        <p className="key-metric-sublabel mt-1 text-base leading-5 text-brand-muted">{sublabel}</p>
      ) : null}
    </div>
  );
}

function renderSingleChart(
  chartId: DashboardChartId,
  d: ReportDashboard,
): React.ReactElement {
  switch (chartId) {
    case "rsu-inscriptions":
      return (
        <Panel
          title={d.charts.rsuInscriptionsMensuelles.title}
          subtitle={`RSU - ${unitLabel(d.charts.rsuInscriptionsMensuelles.unit)}`}
          isPrint
        >
          <RsuChart
            points={d.charts.rsuInscriptionsMensuelles.series}
            trend={d.charts.rsuInscriptionsMensuelles.trend}
          />
        </Panel>
      );
    case "asd-entrees-sorties":
      return (
        <Panel title={d.charts.asdEntreesSorties.title} subtitle="Section 20. ASD - ménages" isPrint>
          <AsdChart points={d.charts.asdEntreesSorties.series} />
        </Panel>
      );
    case "fms-matrice-risque":
      return (
        <Panel title={d.charts.fmsMatriceRisque.title} subtitle="Famille - niveau de risque" isPrint>
          <FmsMatrixChart rows={d.charts.fmsMatriceRisque.rows} />
        </Panel>
      );
    case "menages-bloques-national":
      return (
        <Panel title={d.charts.menagesBloquesNational.title} subtitle="Stock courant par motif" isPrint>
          <BlockedNationalChart rows={d.charts.menagesBloquesNational.rows} />
        </Panel>
      );
    case "flux-regionaux":
      return (
        <Panel title={d.charts.fluxRegionauxAsdAmot.title} subtitle="T1 régions" isPrint>
          <RegionFluxChart rows={d.charts.fluxRegionauxAsdAmot.rows} />
        </Panel>
      );
    case "menages-bloques-regionaux":
      return (
        <Panel title={d.charts.menagesBloquesRegionaux.title} subtitle="Stock courant" isPrint>
          <RegionBlockedChart rows={d.charts.menagesBloquesRegionaux.rows} />
        </Panel>
      );
  }
}

function KpiTile({
  metric,
  sublabel,
  tone,
}: {
  metric: Metric;
  sublabel?: string;
  tone?: "green" | "greenSolid" | "red" | "amber";
}): React.ReactElement {
  const isSolid = tone === "greenSolid";
  const valueColor =
    tone === "red"
      ? "text-brand-danger"
      : tone === "amber"
        ? "text-[#9A6A00]"
        : isSolid
          ? "text-white"
          : "text-brand-ink";
  const badgeColor =
    tone === "red"
      ? "bg-red-50 text-brand-danger"
      : tone === "amber"
        ? "bg-amber-50 text-[#9A6A00]"
        : isSolid
          ? "bg-white/15 text-white"
          : "bg-emerald-50 text-brand-primary";
  const barColor =
    tone === "red" ? "bg-brand-danger/20" : tone === "amber" ? "bg-amber-200" : "bg-emerald-100";
  const delta = metric.percentDisplay;

  return (
    <div
      className={`kpi-tile min-h-[98px] border ${
        isSolid
          ? "border-brand-primary bg-brand-primary text-white shadow-card"
          : "border-brand-border bg-white"
      } p-4`}
    >
      <p className={`text-xs leading-4 ${isSolid ? "text-white/70" : "text-brand-muted"}`}>
        {metric.label}
      </p>
      <p className={`mt-1 text-2xl font-semibold leading-7 ${valueColor}`}>
        {metric.compactDisplay ?? metric.display ?? "-"}
      </p>
      <div className="mt-2 flex min-h-5 flex-wrap items-center gap-2">
        {delta ? (
          <span className={`px-2 py-0.5 text-[11px] font-semibold ${badgeColor}`}>
            {delta}
          </span>
        ) : null}
        {sublabel ? (
          <span className={`text-[11px] ${isSolid ? "text-white/70" : "text-brand-muted"}`}>
            {sublabel}
          </span>
        ) : null}
      </div>
      {!isSolid ? (
        <div className="mt-3 grid grid-cols-3 gap-1">
          <span className={`h-1 ${barColor}`} />
          <span className={`h-1 ${barColor}`} />
          <span className={`h-1 ${barColor}`} />
        </div>
      ) : null}
    </div>
  );
}

function Panel({
  title,
  subtitle,
  exportChartId,
  exportQuery = "",
  canExport = true,
  isPrint = false,
  children,
}: {
  title: string;
  subtitle?: string;
  exportChartId?: DashboardChartId;
  exportQuery?: string;
  canExport?: boolean;
  isPrint?: boolean;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <section className="dashboard-panel border border-brand-border bg-white p-4 print:break-inside-avoid">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-brand-ink">{title}</h2>
          {subtitle ? <p className="mt-1 text-[11px] text-brand-muted">{subtitle}</p> : null}
        </div>
        {exportChartId && canExport && !isPrint ? (
          <a
            href={`/api/reports/dashboard/charts/${exportChartId}/export.png${exportQuery}`}
            download={`rsu-dashboard-${exportChartId}.png`}
            className="inline-flex h-7 items-center justify-center gap-1 border border-brand-border bg-white px-2 text-[11px] font-medium text-brand-ink hover:bg-brand-bg"
          >
            <Download className="h-3 w-3" aria-hidden />
            PNG
          </a>
        ) : !isPrint && canExport ? (
          <span className="text-base leading-none text-brand-muted">...</span>
        ) : null}
      </div>
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
    <div className="dashboard-chart chart-rsu h-[260px]">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: GRAY }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: GRAY }} tickFormatter={formatCompactAxis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} iconType="circle" />
          <Bar dataKey="value" name="Inscrits RNP" fill={GREEN_SOFT} barSize={26} radius={[0, 0, 0, 0]} />
          <Line
            type="monotone"
            dataKey="trend"
            name="Tendance"
            stroke={GREEN_DARK}
            strokeWidth={2}
            dot={{ r: 3, fill: GREEN_DARK, strokeWidth: 0 }}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function AsdChart({ points }: { points: AsdPoint[] }): React.ReactElement {
  return (
    <div className="dashboard-chart chart-asd h-[260px]">
      <ResponsiveContainer>
        <ComposedChart data={points} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10, fill: GRAY }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: GRAY }} tickFormatter={formatCompactAxis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend verticalAlign="top" height={28} wrapperStyle={{ fontSize: 11 }} iconType="circle" />
          <Bar dataKey="netRaw" name="Delta" fill="#D6D6D3" barSize={22} radius={[0, 0, 0, 0]} />
          <Line type="monotone" dataKey="entrantsRaw" name="Entrées" stroke={GREEN} strokeWidth={2} dot={{ r: 3, fill: GREEN, strokeWidth: 0 }} />
          <Line type="monotone" dataKey="sortantsRaw" name="Sorties" stroke={RED} strokeWidth={2} dot={{ r: 3, fill: RED, strokeWidth: 0 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function FmsMatrixChart({ rows }: { rows: FmsMatrixRow[] }): React.ReactElement {
  const groups = groupFmsRows(rows);

  return (
    <div className="fms-reference-chart dashboard-chart chart-fms">
      <div
        className="fms-reference-groups"
        style={{ gridTemplateColumns: `repeat(${Math.max(groups.length, 1)}, minmax(0, 1fr))` }}
      >
        {groups.map((group) => (
          <div className="fms-reference-group" key={group.family}>
            <div className="fms-reference-family">{group.family}</div>
            <div className="fms-reference-rule" />
            <div
              className="fms-reference-bars"
              style={{
                gridTemplateColumns: `repeat(${Math.max(group.rows.length, 1)}, minmax(0, 1fr))`,
              }}
            >
              {group.rows.map((row) => (
                <div className="fms-reference-bar-column" key={`${group.family}-${row.risk}`}>
                  <div className="fms-reference-stack">
                    <div
                      className={`fms-reference-segment fms-reference-leve ${
                        row.levePct < 18 ? "fms-reference-segment-compact" : ""
                      }`}
                      style={{ height: `${row.levePct}%` }}
                    >
                      <span>{formatCompactLabel(row.leve)}</span>
                      <small>{formatPercent(row.levePct)}</small>
                    </div>
                    <div
                      className={`fms-reference-segment fms-reference-confirme ${
                        row.confirmePct < 18 ? "fms-reference-segment-compact" : ""
                      }`}
                      style={{ height: `${row.confirmePct}%` }}
                    >
                      <span>{formatCompactLabel(row.confirme)}</span>
                      <small>{formatPercent(row.confirmePct)}</small>
                    </div>
                  </div>
                  <div className="fms-reference-risk">{row.risk}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="fms-reference-axis" />
      <div className="fms-reference-legend">
        <span><i className="bg-[#D40000]" />Doute confirmé</span>
        <span><i className="bg-[#00572B]" />Doute levé</span>
      </div>
    </div>
  );
}

function BlockedNationalChart({ rows }: { rows: BlockedNationalRow[] }): React.ReactElement {
  return (
    <div className="dashboard-chart chart-blocked-national h-[330px]">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 18, right: 12, left: 0, bottom: 12 }}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="motifBlocage" tick={{ fontSize: 10, fill: GRAY }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 10, fill: GRAY }} tickFormatter={formatCompactAxis} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Bar dataKey="menagesRaw" name="Ménages bloqués" barSize={42}>
            {rows.map((row, index) => (
              <Cell key={row.motifBlocage} fill={index === rows.length - 1 ? RED : index === 1 ? GREEN_SOFT : GREEN} />
            ))}
            <LabelList dataKey="menagesDisplay" position="top" fontSize={11} fill="#14140F" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function RegionFluxChart({ rows }: { rows: RegionFluxRow[] }): React.ReactElement {
  const data = rows.filter((row) => row.entrantsRaw || row.sortantsRaw);
  return (
    <div className="dashboard-chart chart-region-flux h-[320px]">
      <ResponsiveContainer>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 18, left: 0, bottom: 8 }}
        >
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: GRAY }} tickFormatter={formatCompactAxis} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="codeRegion" width={34} tick={{ fontSize: 10, fill: GRAY }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" />
          <Bar dataKey="entrantsRaw" name="Entrants" fill={GREEN} barSize={8} radius={[0, 0, 0, 0]} />
          <Bar dataKey="sortantsRaw" name="Sortants" fill={RED} barSize={8} radius={[0, 0, 0, 0]} />
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
    <div className="dashboard-chart chart-region-blocked h-[320px]">
      <ResponsiveContainer>
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 28, left: 0, bottom: 8 }}
        >
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: GRAY }} tickFormatter={formatCompactAxis} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="codeRegion" width={34} tick={{ fontSize: 10, fill: GRAY }} axisLine={false} tickLine={false} />
          <Tooltip formatter={(value: number) => formatNumber(value)} />
          <Bar dataKey="menagesRaw" name="Bloqués" fill={RED_DARK} barSize={10} radius={[0, 0, 0, 0]}>
            <LabelList dataKey="menagesDisplay" position="right" fontSize={10} fill="#14140F" />
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
    <div className="compact-table mt-3 overflow-hidden border border-brand-border">
      <table className="w-full table-fixed text-[10px]">
        <thead className={headerColor === "green" ? "bg-brand-primary text-white" : "bg-brand-bg text-brand-soft"}>
          <tr>
            {columns.map(([label]) => (
              <th key={label} className="px-3 py-2 text-left font-semibold uppercase tracking-[0.04em]">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-border bg-white">
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index}>
                {columns.map(([label, key]) => (
                  <td key={`${label}-${key}`} className="px-3 py-2 text-brand-soft">
                    {formatCell(row[key])}
                  </td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td className="px-3 py-3 text-brand-muted" colSpan={columns.length}>
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

function emptyMetric(label: string): Metric {
  return { label, display: "-" };
}

function personSublabel(metric?: Metric): string | undefined {
  if (metric?.raw == null || metric.raw <= 0) return undefined;
  const display = metric?.compactDisplay ?? metric?.display;
  if (!display || display === "-") return undefined;
  return `${display} personnes`;
}

function registrationPersonSublabel(prefix: string, metric?: Metric): string {
  if (metric?.raw == null || metric.raw <= 0) return prefix;
  const display = metric?.compactDisplay ?? metric?.display;
  if (!display || display === "-") return prefix;
  return `${prefix} · ${display} pers.`;
}

function traitementFmsSublabel(dashboard: ReportDashboard): string {
  const injected = dashboard.cards.traitementFms.demandesInjectees.compactDisplay
    ?? dashboard.cards.traitementFms.demandesInjectees.display;
  const rate = dashboard.cards.traitementFms.tauxTraitementPct.display;
  if (injected && rate) return `Sur ${injected} injectées (taux ${rate})`;
  if (rate) return `Taux ${rate}`;
  return "";
}

function resultatFmsSublabel(metric: Metric): string {
  const display = metric.display ?? metric.compactDisplay;
  return display ? `${display} des traitements` : "";
}

function unitLabel(unit?: string): string {
  return String(unit || "MENAGES").toUpperCase() === "PERSONNES" ? "personnes" : "ménages";
}

function dashboardDateQuery(dashboard: ReportDashboard): string {
  const params = new URLSearchParams();
  const range = dashboard.meta.dateRange;
  if (range?.startDate) params.set("startDate", range.startDate);
  if (range?.endDate) params.set("endDate", range.endDate);
  const query = params.toString();
  return query ? `?${query}` : "";
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

function formatCompactLabel(value: unknown): string {
  const numeric = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "";
  return formatCompactAxis(numeric);
}

function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function shortRisk(value: string): string {
  const lower = value.toLowerCase();
  if (lower.includes("élev") || lower.includes("elev")) return "Elevé";
  if (lower.includes("moy")) return "Moyen";
  return value.slice(0, 8);
}

function familyShortLabel(value: string): string {
  return value;
}

function groupFmsRows(rows: FmsMatrixRow[]): {
  family: string;
  rows: {
    risk: string;
    confirme: number;
    leve: number;
    confirmePct: number;
    levePct: number;
  }[];
}[] {
  const groups = new Map<string, {
    risk: string;
    confirme: number;
    leve: number;
    confirmePct: number;
    levePct: number;
  }[]>();

  for (const row of rows) {
    const family = familyShortLabel(row.typeFamille);
    const total = row.douteConfirmeRaw + row.douteLeveRaw;
    const confirmePct = total > 0 ? (row.douteConfirmeRaw / total) * 100 : 0;
    const levePct = total > 0 ? (row.douteLeveRaw / total) * 100 : 0;
    const next = {
      risk: shortRisk(row.niveauRisque),
      confirme: row.douteConfirmeRaw,
      leve: row.douteLeveRaw,
      confirmePct,
      levePct,
    };
    groups.set(family, [...(groups.get(family) ?? []), next]);
  }

  return [...groups.entries()]
    .map(([family, familyRows]) => ({
      family,
      rows: familyRows.sort((a, b) => riskOrder(a.risk) - riskOrder(b.risk)),
    }));
}

function riskOrder(value: string): number {
  const lower = value.toLowerCase();
  if (lower.includes("elev") || lower.includes("élev")) return 0;
  if (lower.includes("moy")) return 1;
  return 2;
}
