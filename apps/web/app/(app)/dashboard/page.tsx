import Link from "next/link";
import {
  BellRing,
  ClipboardList,
  DoorOpen,
  MessageSquareWarning,
  RefreshCcw,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";
import { DashboardFilters } from "@/components/kpi/dashboard-filters";
import { ExportDownloadButton } from "@/components/export-download-button";
import { KpiPanel } from "@/components/kpi/kpi-panel";
import { Card, CardContent } from "@/components/ui/card";
import {
  exportPdfHref,
  getKpiFilters,
  getOverview,
  readGlobalFilters,
  type SearchParams,
} from "@/lib/kpi-api";

export const dynamic = "force-dynamic";

const SECTION_CARDS = [
  { slug: "acces", label: "Accès", icon: DoorOpen },
  { slug: "inscription", label: "Inscription", icon: ClipboardList },
  { slug: "fiabilisation-sources", label: "Fiabilisation des sources", icon: ShieldCheck },
  { slug: "maj-rescoring", label: "Mise à jour & rescoring", icon: RefreshCcw },
  { slug: "notification", label: "Notification", icon: BellRing },
  { slug: "recours-reclamations", label: "Recours & réclamations", icon: MessageSquareWarning },
  { slug: "controle-qualite", label: "Contrôle qualité", icon: ShieldQuestion },
];

export default async function DashboardOverview({
  searchParams,
}: {
  searchParams: SearchParams;
}): Promise<React.ReactElement> {
  const filters = readGlobalFilters(searchParams);
  const [filterOptions, overview] = await Promise.all([
    getKpiFilters(),
    getOverview(filters),
  ]);

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <h1 className="text-sm font-semibold text-brand-ink">Vue d&apos;ensemble</h1>
        <ExportDownloadButton
          href={exportPdfHref("overview", filters)}
          filename="rsu-kpi-vue-ensemble.pdf"
          className="inline-flex h-8 items-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg disabled:cursor-not-allowed disabled:opacity-50"
        >
          Exporter en PDF
        </ExportDownloadButton>
      </header>

      <div className="space-y-6 px-5 py-8">
        <section>
          <h2 className="text-2xl font-semibold tracking-normal text-brand-ink">
            Dashboard de pilotage des processus du RSU
          </h2>
          <p className="mt-2 text-sm text-brand-muted">
            Signaux de pilotage clés pour les 18 KPI du Registre Social Unifié.
          </p>
        </section>

        <DashboardFilters options={filterOptions} />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {overview.cards.map((card) => (
            <KpiPanel
              key={card.code}
              card={card}
              compact
              href={`/dashboard/${card.section}/${card.code}`}
            />
          ))}
        </section>

        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-brand-primary">
            Processus RSU
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {SECTION_CARDS.map((section) => (
              <Link key={section.slug} href={`/dashboard/${section.slug}`} className="block">
                <Card className="h-full transition hover:border-brand-border-strong">
                  <CardContent className="flex items-center gap-3 p-5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                      <section.icon className="h-4 w-4" aria-hidden />
                    </span>
                    <span className="text-sm font-semibold text-brand-ink">{section.label}</span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
