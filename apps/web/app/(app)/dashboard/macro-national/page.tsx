import { apiFetch } from "@/lib/api";
import type { MacroNationalPayload } from "@/lib/types/macro-national";
import { KpiCard } from "@/components/kpi-card";
import { NoData } from "@/components/no-data";
import { Section } from "@/components/section";
import { Card } from "@/components/ui/card";
import { formatBigNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function MacroNationalPage(): Promise<React.ReactElement> {
  const data = await apiFetch<MacroNationalPayload>(
    "/api/boards/macro-national/data",
  );

  const k = data.inscriptions_kpis;
  const ps = data.programmes_sociaux;
  const fms = data.fms_kpis;
  const rf = data.radiation_fraude;
  const rs = data.rescoring;
  const eb = data.economie_budgetaire;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-brand-dark">
            Tableau de bord hebdomadaire de suivi RSU
          </h1>
          <p className="mt-1 text-sm text-brand-muted">
            {data.reporting_date
              ? `Semaine du ${new Date(data.reporting_date).toLocaleDateString("fr-FR")}`
              : "Aucune donnée chargée"}
          </p>
        </div>
        <button
          type="button"
          className="inline-flex h-10 items-center justify-center rounded-md bg-brand-primary px-4 text-sm font-medium text-white hover:bg-brand-dark"
          disabled
          title="Chargement de données disponible à l'étape 5"
        >
          Charger des données
        </button>
      </header>

      <Section title="Chiffres clés des inscriptions">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Ménages inscrits"
            value={k?.total_menages ?? null}
            sublabel={
              k ? `${formatBigNumber(k.total_personnes)} personnes` : undefined
            }
          />
          <KpiCard
            label="Personnes inscrites"
            value={k?.total_personnes ?? null}
          />
          <KpiCard
            label="Nouveaux ménages (mois)"
            value={k?.new_menages_last_month ?? null}
          />
          <KpiCard
            label="Variation mensuelle"
            value={
              k?.new_menages_last_month_pct_change != null
                ? Math.round(k.new_menages_last_month_pct_change)
                : null
            }
            sublabel="%"
          />
        </div>
      </Section>

      <Section title="Programmes sociaux">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <KpiCard
            label="Bénéficiaires Tadamon"
            value={ps?.tadamon_beneficiaries ?? null}
          />
          <KpiCard
            label="Bénéficiaires AMO"
            value={ps?.amo_beneficiaries ?? null}
          />
        </div>
      </Section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Dynamique des inscriptions au RSU
          </h3>
          {data.monthly_evolution?.length ? (
            <div className="mt-4 text-xs text-brand-muted">
              {data.monthly_evolution.length} points mensuels.
            </div>
          ) : (
            <NoData className="mt-4" />
          )}
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Dynamique d&apos;entrées / sorties (ASD)
          </h3>
          {data.entries_exits?.length ? (
            <div className="mt-4 text-xs text-brand-muted">
              {data.entries_exits.length} points mensuels.
            </div>
          ) : (
            <NoData className="mt-4" />
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Évolution mensuelle des inscriptions
          </h3>
          <NoData className="mt-4" />
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Évolution mensuelle ASD
          </h3>
          <NoData className="mt-4" />
        </Card>
      </div>

      <Section title="Traitement FMS">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <KpiCard label="Demandes traitées" value={fms?.demandes_traitees ?? null} />
          <KpiCard
            label="Doute confirmé"
            value={fms?.doute_confirme ?? null}
            tone="danger"
          />
          <KpiCard
            label="Doute levé"
            value={fms?.doute_leve ?? null}
            tone="positive"
          />
        </div>
      </Section>

      <Section title="Radiation pour fraude">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <KpiCard
            label="Ménages radiés"
            value={rf?.menages_radies ?? null}
            tone="danger"
          />
          <KpiCard
            label="Personnes radiées"
            value={rf?.personnes_radiees ?? null}
            tone="danger"
          />
        </div>
      </Section>

      <Section title="Rescoring">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <KpiCard
            label="Ménages rescorés"
            value={rs?.menages_rescores ?? null}
          />
          <KpiCard
            label="Personnes rescorées"
            value={rs?.personnes_rescorees ?? null}
          />
        </div>
      </Section>

      <Section title="Économie budgétaire totale">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <KpiCard
            label="Fraude"
            value={eb?.fraude ?? null}
            tone="positive"
            sublabel="MAD"
          />
          <KpiCard
            label="Rescoring"
            value={eb?.rescoring ?? null}
            tone="positive"
            sublabel="MAD"
          />
          <KpiCard
            label="Total optimisation"
            value={eb?.total ?? null}
            tone="positive"
            sublabel="MAD"
          />
        </div>
      </Section>

      <Card className="p-5">
        <h3 className="text-sm font-semibold text-brand-dark">
          Résultats des traitements FMS par niveau de risque
        </h3>
        {data.fms_buckets?.length ? (
          <div className="mt-4 text-xs text-brand-muted">
            {data.fms_buckets.length} buckets.
          </div>
        ) : (
          <NoData className="mt-4" />
        )}
      </Card>

      <Card className="p-5">
        <h3 className="text-sm font-semibold text-brand-dark">Ménages bloqués</h3>
        {data.menages_bloques_categories?.length ? (
          <div className="mt-4 text-xs text-brand-muted">
            {data.menages_bloques_categories.length} catégories.
          </div>
        ) : (
          <NoData className="mt-4" />
        )}
      </Card>

      <Card className="p-5">
        <h3 className="text-sm font-semibold text-brand-dark">
          Entrants / Sortants ASD + AMO Tadamon par région
        </h3>
        {data.region_flux?.length ? (
          <div className="mt-4 text-xs text-brand-muted">
            {data.region_flux.length} régions.
          </div>
        ) : (
          <NoData className="mt-4" />
        )}
      </Card>

      <Card className="p-5">
        <h3 className="text-sm font-semibold text-brand-dark">
          Ménages bloqués par région
        </h3>
        {data.region_bloques?.length ? (
          <div className="mt-4 text-xs text-brand-muted">
            {data.region_bloques.length} régions.
          </div>
        ) : (
          <NoData className="mt-4" />
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Top 5 provinces: inscriptions nettes
          </h3>
          {data.top_provinces_inscriptions?.length ? (
            <div className="mt-4 text-xs text-brand-muted">
              {data.top_provinces_inscriptions.length} provinces.
            </div>
          ) : (
            <NoData className="mt-4" />
          )}
        </Card>
        <Card className="p-5">
          <h3 className="text-sm font-semibold text-brand-dark">
            Top 5 provinces: ménages bloqués
          </h3>
          {data.top_provinces_bloques?.length ? (
            <div className="mt-4 text-xs text-brand-muted">
              {data.top_provinces_bloques.length} provinces.
            </div>
          ) : (
            <NoData className="mt-4" />
          )}
        </Card>
      </div>

      <footer className="space-y-1 border-t border-brand-border pt-4 text-xs text-brand-muted">
        <p>
          Note 1: les bénéficiaires CNRA non déclarés peuvent ne pas figurer
          dans les totaux de ce rapport.
        </p>
        <p>
          Note 2: les bénéficiaires CNSS non déclarés peuvent ne pas figurer
          dans les totaux de ce rapport.
        </p>
      </footer>
    </div>
  );
}
