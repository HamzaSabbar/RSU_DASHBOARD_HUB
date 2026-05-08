import Link from "next/link";
import {
  Bell,
  CalendarDays,
  ChartNoAxesColumnIncreasing,
} from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import type { ReportDashboard } from "@/components/report-dashboard-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type BoardSummary = {
  slug: string;
  title: string;
  description: string;
  last_updated: string | null;
  status: "ready" | "no_data";
};

type HubMetric = {
  label: string;
  compactDisplay?: string | null;
  display?: string | null;
  percentDisplay?: string | null;
};

export const dynamic = "force-dynamic";

export default async function DashboardHub(): Promise<React.ReactElement> {
  const [boards, dashboard, session] = await Promise.all([
    apiFetch<BoardSummary[]>("/api/boards"),
    getDashboard(),
    auth(),
  ]);
  const readyBoards = boards.filter((board) => board.status === "ready").length;
  const displayName =
    session?.user?.name ??
    session?.user?.email?.split("@")[0]?.replace(/[._-]+/g, " ") ??
    "";
  const summaryCards: HubMetric[] = dashboard
    ? [
        dashboard.cards.inscriptions.rnpPersonnesTotal,
        dashboard.cards.inscriptions.rsuMenagesTotal,
        dashboard.cards.programmesSociaux.asdMenagesActifs,
        dashboard.cards.economieBudgetaire.total,
      ]
    : [
        { label: "Tableaux actifs", compactDisplay: String(readyBoards), percentDisplay: null },
        { label: "Espaces configurés", compactDisplay: String(boards.length), percentDisplay: null },
        {
          label: "Dernière mise à jour",
          compactDisplay: latestBoardDate(boards),
          percentDisplay: null,
        },
        { label: "Statut plateforme", compactDisplay: "Opérationnel", percentDisplay: null },
      ];

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <h1 className="text-sm font-semibold text-brand-ink">Hub</h1>
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-2 text-sm text-brand-ink">
            <Bell className="h-4 w-4" aria-hidden />
            3
          </span>
        </div>
      </header>

      <div className="space-y-7 px-5 py-8">
        <section>
          <h2 className="text-3xl font-semibold tracking-normal text-brand-ink">
            Bonjour{displayName ? `, ${displayName}` : ""}
          </h2>
          <p className="mt-2 text-base text-brand-muted">
            {readyBoards} espaces de travail actifs - semaine 17 / 2026.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {summaryCards.map((metric) => (
            <SummaryCard
              key={metric.label}
              label={metric.label}
              value={metric.compactDisplay ?? metric.display ?? "-"}
              delta={metric.percentDisplay}
            />
          ))}
        </section>

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-brand-ink">Tableaux de bord</h2>
            <div className="flex rounded-md bg-white p-1 text-xs text-brand-muted">
              <span className="rounded bg-brand-bg px-3 py-1 font-medium text-brand-ink">Tous</span>
              <span className="px-3 py-1">Récents</span>
              <span className="px-3 py-1">Favoris</span>
            </div>
          </div>

          {boards.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center text-sm text-brand-muted">
                Aucun tableau disponible pour le moment.
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {boards.map((board) => (
                <Link key={board.slug} href={`/dashboard/${board.slug}`} className="group block">
                  <Card className="h-full rounded-lg transition group-hover:border-brand-border-strong group-hover:bg-white">
                    <CardContent className="flex min-h-[118px] items-start gap-4 p-5">
                      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                        <ChartNoAxesColumnIncreasing className="h-4 w-4" aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-semibold text-brand-ink">{board.title}</h3>
                          <Badge variant={board.status === "ready" ? "ready" : "empty"}>
                            {board.status === "ready" ? "À jour" : "En attente"}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-brand-muted">{board.description}</p>
                        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs text-brand-muted">
                          <span>/{board.slug}</span>
                          <span>
                            {board.last_updated
                              ? `Mis à jour ${new Date(board.last_updated).toLocaleDateString("fr-FR")}`
                              : "Aucune mise à jour"}
                          </span>
                        </div>
                      </div>
                      <div className="hidden text-right sm:block">
                        <p className="text-2xl font-semibold text-brand-ink">
                          {board.slug === "macro-national" && dashboard
                            ? dashboard.cards.inscriptions.rnpPersonnesTotal.compactDisplay ??
                              dashboard.cards.inscriptions.rnpPersonnesTotal.display ??
                              "-"
                            : board.status === "ready"
                              ? "Actif"
                              : "-"}
                        </p>
                        <p className="text-[10px] uppercase text-brand-muted">
                          {board.slug === "macro-national" ? "RNP" : "Statut"}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function SummaryCard({
  label,
  value,
  delta,
}: {
  label: string;
  value: string;
  delta?: string | null;
}): React.ReactElement {
  return (
    <Card className="rounded-lg">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm text-brand-muted">{label}</p>
          <CalendarDays className="h-4 w-4 text-brand-muted" aria-hidden />
        </div>
        <p className="mt-2 text-3xl font-semibold text-brand-ink">{value}</p>
        {delta ? (
          <span className="mt-2 inline-flex rounded bg-emerald-50 px-2 py-1 text-xs font-semibold text-brand-primary">
            {delta}
          </span>
        ) : null}
      </CardContent>
    </Card>
  );
}

async function getDashboard(): Promise<ReportDashboard | null> {
  try {
    return await apiFetch<ReportDashboard>("/api/reports/dashboard");
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

function latestBoardDate(boards: BoardSummary[]): string {
  const latest = boards
    .map((board) => board.last_updated)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  return latest ? new Date(latest).toLocaleDateString("fr-FR") : "-";
}
