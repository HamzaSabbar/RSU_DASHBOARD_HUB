"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type SocialFilterOptions = {
  release_key: string;
  period_start: string;
  period_end: string;
  subjects: { value: string; label: string }[];
  regions: { id: number; label: string; parent_id: number | null }[];
  provinces: { id: number; label: string; parent_id: number | null }[];
};

export type SocialDashboardData = {
  release_key: string;
  filters: {
    subject: "ALL" | "ASD" | "AMOT";
    region_id: number | null;
    province_id: number | null;
    start_date: string;
    end_date: string;
    granularity: "day" | "week" | "month" | "quarter";
  };
  summary: {
    eligible_households: number;
    programs: {
      program_code: string;
      entries: number;
      exits: number;
      net: number;
      eligible_households: number;
    }[];
  };
  flow: {
    program_code: string;
    period: string;
    entries: number;
    exits: number;
    net: number;
  }[];
  volatility: {
    program_code: string;
    band: string;
    band_order: number;
    crossings: number;
    percentage: number;
  }[];
  territories: {
    province_id: number | null;
    province: string;
    entries: number;
    exits: number;
    net: number;
  }[];
  methodology: {
    crossing_scope: string;
    score_bucket: string;
    cutoff_date: string;
    thresholds: Record<string, number>;
    eligibility: string;
  };
};

type Props = {
  options: SocialFilterOptions;
  data: SocialDashboardData;
};

const PROGRAM_LABELS: Record<string, string> = { ASD: "ASD", AMOT: "AMO T" };
const PROGRAM_COLORS: Record<string, { entries: string; exits: string }> = {
  ASD: { entries: "#1a3d2b", exits: "#c9a84c" },
  AMOT: { entries: "#0f6e56", exits: "#d97b3a" },
};
const BAND_ORDER = ["<1", "1-5", "5-10", "10-20", "20-30", "30-50", "51+"];

export function SocialProgramsRescoringDashboard({
  options,
  data,
}: Props): React.ReactElement {
  const programs = data.filters.subject === "ALL" ? ["ASD", "AMOT"] : [data.filters.subject];
  const totals = new Map(data.summary.programs.map((item) => [item.program_code, item]));
  const volatility = BAND_ORDER.map((band) => {
    const row: Record<string, string | number> = { band };
    for (const item of data.volatility.filter((candidate) => candidate.band === band)) {
      row[item.program_code] = item.percentage;
    }
    return row;
  });
  const periodLabel = `${formatDate(data.filters.start_date)} – ${formatDate(data.filters.end_date)}`;

  return (
    <div className="overflow-hidden rounded-sm border border-[#dde3d8] bg-[#f4f6f3] shadow-sm">
      <section className="flex flex-wrap items-center justify-between gap-4 border-b-[3px] border-[#c9a84c] bg-[#1a3d2b] px-5 py-4 text-white">
        <div>
          <h2 className="text-[15px] font-semibold text-white">
            Programmes sociaux — Rescoring
          </h2>
          <p className="mt-1 text-[11px] text-[#9fc9a8]">
            Éligibilité · franchissements de seuil · volatilité · lecture territoriale
          </p>
        </div>
        <span className="rounded bg-[#c9a84c] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#1a3d2b]">
          {periodLabel}
        </span>
      </section>

      <form
        method="get"
        className="flex flex-wrap items-end gap-3 border-b border-[#dde3d8] bg-white px-5 py-3"
      >
        <SelectFilter
          label="Sujet"
          name="subject"
          defaultValue={data.filters.subject}
          options={options.subjects.map((item) => ({ value: item.value, label: item.label }))}
        />
        <SelectFilter
          label="Région"
          name="region_id"
          defaultValue={data.filters.region_id?.toString() ?? ""}
          options={[
            { value: "", label: "Toutes les régions" },
            ...options.regions.map((item) => ({ value: String(item.id), label: item.label })),
          ]}
        />
        <SelectFilter
          label="Province"
          name="province_id"
          defaultValue={data.filters.province_id?.toString() ?? ""}
          options={[
            { value: "", label: "Toutes les provinces" },
            ...options.provinces.map((item) => ({ value: String(item.id), label: item.label })),
          ]}
        />
        <DateFilter label="Du" name="start_date" value={data.filters.start_date} />
        <DateFilter label="Au" name="end_date" value={data.filters.end_date} />
        <SelectFilter
          label="Pas"
          name="granularity"
          defaultValue={data.filters.granularity}
          options={[
            { value: "day", label: "Jour" },
            { value: "week", label: "Semaine" },
            { value: "month", label: "Mois" },
            { value: "quarter", label: "Trimestre" },
          ]}
        />
        <button
          type="submit"
          className="h-8 rounded bg-[#1a3d2b] px-3 text-xs font-semibold text-white hover:bg-[#24543b]"
        >
          Appliquer
        </button>
      </form>

      <section className={`grid border-b border-[#dde3d8] bg-white sm:grid-cols-2 ${programs.length === 2 ? "lg:grid-cols-5" : "lg:grid-cols-3"}`}>
        <KpiTile label="Ménages éligibles" value={compact(data.summary.eligible_households)} sublabel={`au ${formatDate(data.filters.end_date)}`} highlight />
        {programs.flatMap((program) => [
          <ProgramKpi key={`${program}-entries`} program={program} kind="entries" totals={totals.get(program)} period={periodLabel} />,
          <ProgramKpi key={`${program}-exits`} program={program} kind="exits" totals={totals.get(program)} period={periodLabel} warn />,
        ])}
      </section>

      <section className={`grid border-b border-[#dde3d8] bg-white ${programs.length > 1 ? "xl:grid-cols-2" : ""}`}>
        {programs.map((program) => (
          <ChartPanel
            key={program}
            title={`${PROGRAM_LABELS[program]} — Entrées / Sorties`}
            subtitle={`Franchissements du seuil sur la période sélectionnée · net ${signed(totals.get(program)?.net ?? 0)}`}
          >
            <FlowChart rows={data.flow.filter((item) => item.program_code === program)} program={program} />
            <Legend
              items={[
                { label: "Entrées", color: PROGRAM_COLORS[program].entries },
                { label: "Sorties", color: PROGRAM_COLORS[program].exits },
              ]}
            />
          </ChartPanel>
        ))}
      </section>

      <section className="grid border-t border-[#dde3d8] bg-white xl:grid-cols-2">
        <ChartPanel
          title="Volatilité du scoring"
          subtitle="Répartition des franchissements selon l’amplitude absolue de la variation ISE"
          bottom
        >
          <div className="h-48 w-full">
            <ResponsiveContainer>
              <BarChart data={volatility} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e8ede6" />
                <XAxis dataKey="band" tick={{ fontSize: 10, fill: "#8a9e87" }} />
                <YAxis tick={{ fontSize: 10, fill: "#8a9e87" }} tickFormatter={(value: number) => `${value}%`} />
                <Tooltip formatter={(value: number) => `${value.toLocaleString("fr-FR")} %`} />
                {programs.map((program) => (
                  <Bar key={program} dataKey={program} name={PROGRAM_LABELS[program]} fill={PROGRAM_COLORS[program].entries} radius={[2, 2, 0, 0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <Legend items={programs.map((program) => ({ label: PROGRAM_LABELS[program], color: PROGRAM_COLORS[program].entries, block: true }))} />
          <p className="mt-3 border-t border-[#f0f2ee] pt-2 text-[10px] text-[#6b7c6a]">
            Bandes exprimées en centièmes de point ISE : &lt;1 = variation inférieure à 0,01 point, 51+ = 0,50 point ou plus.
          </p>
        </ChartPanel>

        <section className="border-t border-[#dde3d8] bg-white px-5 py-4 xl:border-l xl:border-t-0">
          <PanelHeading title="Lecture territoriale" subtitle="Provinces classées par amplitude du solde entrées–sorties" />
          <div className="max-h-[270px] overflow-auto">
            <table className="mt-2 w-full border-collapse text-[11px]">
              <thead>
                <tr>
                  <TableHeader>Province</TableHeader>
                  <TableHeader>Entrées</TableHeader>
                  <TableHeader>Sorties</TableHeader>
                  <TableHeader>Net</TableHeader>
                </tr>
              </thead>
              <tbody>
                {data.territories.map((row) => (
                  <tr key={`${row.province_id ?? "na"}-${row.province}`}>
                    <TableCell>{row.province}</TableCell>
                    <TableCell>{integer(row.entries)}</TableCell>
                    <TableCell>{integer(row.exits)}</TableCell>
                    <TableCell className={row.net >= 0 ? "font-semibold text-[#1a6b35]" : "font-semibold text-[#a1281e]"}>
                      {signed(row.net)}
                    </TableCell>
                  </tr>
                ))}
                {data.territories.length === 0 ? (
                  <tr><td className="px-2 py-5 text-center text-brand-muted" colSpan={4}>Aucun franchissement pour ces filtres.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-2 bg-[#1a3d2b] px-5 py-2 text-[10px]">
        <span className="text-[#9fc9a8]">
          Source CSV RSU · moyenne 30 jours · adhésion programme courante · version {data.release_key}
        </span>
        <span className="font-semibold uppercase tracking-[0.1em] text-[#c9a84c]">RSU — Données publiées</span>
      </footer>
    </div>
  );
}

function FlowChart({ rows, program }: { rows: SocialDashboardData["flow"]; program: string }): React.ReactElement {
  return (
    <div className="h-[210px] w-full">
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#e8ede6" />
          <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#8a9e87" }} tickFormatter={shortPeriod} />
          <YAxis tick={{ fontSize: 10, fill: "#8a9e87" }} tickFormatter={compact} />
          <Tooltip labelFormatter={(value: string) => formatDate(value)} formatter={(value: number) => integer(value)} />
          <Line type="monotone" dataKey="entries" name="Entrées" stroke={PROGRAM_COLORS[program].entries} strokeWidth={2} dot={{ r: 2.5 }} />
          <Line type="monotone" dataKey="exits" name="Sorties" stroke={PROGRAM_COLORS[program].exits} strokeWidth={2} strokeDasharray="5 3" dot={{ r: 2.5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ProgramKpi({ program, kind, totals, period, warn = false }: {
  program: string;
  kind: "entries" | "exits";
  totals?: SocialDashboardData["summary"]["programs"][number];
  period: string;
  warn?: boolean;
}): React.ReactElement {
  return <KpiTile label={`${kind === "entries" ? "Entrées" : "Sorties"} ${PROGRAM_LABELS[program]}`} value={compact(totals?.[kind] ?? 0)} sublabel={period} warn={warn} />;
}

function KpiTile({ label, value, sublabel, warn = false, highlight = false }: { label: string; value: string; sublabel: string; warn?: boolean; highlight?: boolean }): React.ReactElement {
  return (
    <div className={`min-h-[102px] border-b border-r border-[#dde3d8] px-4 py-3 last:border-r-0 lg:border-b-0 ${warn ? "bg-[#fdf6ed]" : highlight ? "bg-[#f0f7f2]" : "bg-white"}`}>
      <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.07em] text-[#6b7c6a]">{label}</div>
      <div className={`font-mono text-[22px] font-semibold leading-none ${warn ? "text-[#b85c1a]" : "text-[#1a3d2b]"}`}>{value}</div>
      <div className="mt-2 text-[10px] text-[#8a9e87]">{sublabel}</div>
    </div>
  );
}

function SelectFilter({ label, name, defaultValue, options }: { label: string; name: string; defaultValue: string; options: { value: string; label: string }[] }): React.ReactElement {
  return (
    <label className="grid gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[#6b7c6a]">{label}</span>
      <select name={name} defaultValue={defaultValue} className="h-8 max-w-[220px] rounded border border-[#c5cfbf] bg-[#f9faf8] px-2 text-xs text-[#2c3e2d] outline-none">
        {options.map((option) => <option key={`${name}-${option.value}`} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function DateFilter({ label, name, value }: { label: string; name: string; value: string }): React.ReactElement {
  return (
    <label className="grid gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-[0.06em] text-[#6b7c6a]">{label}</span>
      <input type="date" name={name} defaultValue={value} className="h-8 rounded border border-[#c5cfbf] bg-[#f9faf8] px-2 text-xs text-[#2c3e2d] outline-none" />
    </label>
  );
}

function ChartPanel({ title, subtitle, children, bottom = false }: { title: string; subtitle: string; children: React.ReactNode; bottom?: boolean }): React.ReactElement {
  return <section className={`border-b border-r border-[#dde3d8] bg-white px-5 py-4 last:border-r-0 xl:border-b-0 ${bottom ? "xl:border-r" : ""}`}><PanelHeading title={title} subtitle={subtitle} />{children}</section>;
}

function PanelHeading({ title, subtitle }: { title: string; subtitle: string }): React.ReactElement {
  return <div className="mb-3"><h3 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-[#1a3d2b]"><span className="h-3 w-[3px] rounded-sm bg-[#1a3d2b]" aria-hidden />{title}</h3><p className="mt-1 text-[10px] text-[#8a9e87]">{subtitle}</p></div>;
}

function Legend({ items }: { items: { label: string; color: string; block?: boolean }[] }): React.ReactElement {
  return <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-[#6b7c6a]">{items.map((item) => <span key={item.label} className="flex items-center gap-1"><span className={item.block ? "h-2.5 w-2.5 rounded-sm" : "h-0.5 w-3.5"} style={{ backgroundColor: item.color }} aria-hidden />{item.label}</span>)}</div>;
}

function TableHeader({ children }: { children: React.ReactNode }): React.ReactElement {
  return <th className="sticky top-0 border-b border-[#dde3d8] bg-[#f4f6f3] px-2 py-1.5 text-left text-[10px] font-semibold uppercase tracking-[0.06em] text-[#6b7c6a]">{children}</th>;
}

function TableCell({ children, className = "" }: { children: React.ReactNode; className?: string }): React.ReactElement {
  return <td className={`border-b border-[#f0f2ee] px-2 py-1.5 font-mono text-[11px] ${className}`}>{children}</td>;
}

function compact(value: number): string {
  return new Intl.NumberFormat("fr-FR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function integer(value: number): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(value);
}

function signed(value: number): string {
  return `${value > 0 ? "+" : ""}${integer(value)}`;
}

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function shortPeriod(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", { month: "short", year: "2-digit" }).format(date);
}
