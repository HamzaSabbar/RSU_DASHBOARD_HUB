import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  Calculator,
  Database,
  LineChart,
  TableProperties,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type MethodologyItem = {
  name: string;
  purpose: string;
  source: string;
  calculation: string[];
  note?: string;
};

type MethodologySection = {
  title: string;
  description: string;
  items: MethodologyItem[];
};

const scopeRules = [
  {
    title: "Période sélectionnée",
    body: "Les flux utilisent une date_evenement interne dans l'intervalle choisi. Pour les fichiers client simplifiés, cette date est dérivée de fin_periode.",
  },
  {
    title: "Cumul chargé",
    body: "Les KPI cumulés sont calculés en additionnant les faits actifs dans l'intervalle sélectionné. Les anciennes feuilles de stock restent lisibles uniquement pour compatibilité.",
  },
  {
    title: "Valeurs vides",
    body: "Si aucune ligne ne correspond à la période ou si un dénominateur vaut 0, la valeur est vide ou le dashboard affiche qu'aucune donnée n'est disponible.",
  },
];

const kpiSections: MethodologySection[] = [
  {
    title: "Inscriptions et registre",
    description:
      "Ces KPI mesurent la taille cumulée des registres et le rythme des nouvelles inscriptions RNP.",
    items: [
      {
        name: "RNP - personnes",
        purpose:
          "Afficher le cumul des personnes inscrites au RNP dans les données chargées.",
        source: "11_RNP_Nouvelles_Inscriptions",
        calculation: [
          "Filtrer code_registre = RNP",
          "Filtrer type_unite = PERSONNES",
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_nouvelles_inscriptions)",
        ],
      },
      {
        name: "RSU - ménages",
        purpose:
          "Afficher le cumul des ménages/familles inscrits au RSU dans les données chargées.",
        source: "12_RSU_Nouvelles_Inscriptions",
        calculation: [
          "Filtrer code_registre = RSU",
          "Filtrer type_unite = MENAGES",
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_nouvelles_inscriptions)",
        ],
      },
      {
        name: "RSU - personnes couvertes",
        purpose:
          "Donner, si la source le fournit, le volume de personnes couvertes par les ménages RSU affichés sur le dashboard.",
        source: "10_RSU / Stock RNP/RSU",
        calculation: [
          "Filtrer code_registre = RSU",
          "Filtrer type_unite = PERSONNES",
          "Prendre le stock le plus récent avec date_reference <= date_reference_donnees",
          "KPI = total_cumule",
        ],
      },
      {
        name: "Nouvelles inscriptions RNP",
        purpose:
          "Suivre les nouvelles inscriptions individuelles RNP du mois courant.",
        source: "11_RNP_Nouvelles_Inscriptions",
        calculation: [
          "Utiliser type_unite = PERSONNES si la colonne est absente",
          "Filtrer mois_evenement = mois_reporting_courant",
          "KPI = SUM(nb_nouvelles_inscriptions)",
        ],
        note: "Le nom de feuille legacy 11_RSU_Nouvelles_Inscriptions est encore accepté, mais les nouvelles données doivent être libellées RNP.",
      },
      {
        name: "Evolution vs mois précédent",
        purpose:
          "Comparer les nouvelles inscriptions du mois courant avec le mois précédent disponible.",
        source: "11_RNP_Nouvelles_Inscriptions",
        calculation: [
          "delta = inscriptions_mois_courant - inscriptions_mois_precedent",
          "delta_pct = delta / inscriptions_mois_precedent",
        ],
        note: "Si le mois précédent vaut 0, le pourcentage est laissé vide.",
      },
    ],
  },
  {
    title: "Programmes sociaux",
    description:
      "Ces KPI donnent le net cumulé des bénéficiaires ASD et AMO Tadamon dans la période chargée.",
    items: [
      {
        name: "ASD - ménages actifs",
        purpose:
          "Afficher le nombre de ménages actifs dans le programme ASD à la date de référence.",
        source: "21_ASD_Flux",
        calculation: [
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)",
        ],
      },
      {
        name: "ASD - personnes actives",
        purpose:
          "Afficher le nombre de personnes couvertes par les ménages ASD actifs.",
        source: "21_ASD_Flux",
        calculation: [
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_entrants_personnes) - SUM(nb_sortants_personnes)",
        ],
      },
      {
        name: "AMO Tadamon - ménages actifs",
        purpose:
          "Afficher le nombre de ménages actifs dans le programme AMO Tadamon.",
        source: "31_AMO_Tadamon_Flux",
        calculation: [
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)",
        ],
      },
      {
        name: "AMO Tadamon - personnes actives",
        purpose:
          "Afficher le nombre de personnes couvertes par les ménages AMO Tadamon actifs.",
        source: "31_AMO_Tadamon_Flux",
        calculation: [
          "Filtrer date_evenement dans la période sélectionnée",
          "KPI = SUM(nb_entrants_personnes) - SUM(nb_sortants_personnes)",
        ],
      },
    ],
  },
  {
    title: "Traitement FMS",
    description:
      "Ces KPI suivent le volume traité par le processus FMS et la répartition des résultats.",
    items: [
      {
        name: "Demandes injectées FMS",
        purpose:
          "Mesurer le volume total de demandes envoyées au traitement FMS.",
        source: "40_FMS / Traitement FMS",
        calculation: ["KPI = SUM(demandes_injectees)"],
      },
      {
        name: "Demandes traitées FMS",
        purpose:
          "Mesurer le volume de demandes FMS déjà traitées.",
        source: "40_FMS / Traitement FMS",
        calculation: ["KPI = SUM(demandes_traitees)"],
      },
      {
        name: "Taux de traitement FMS",
        purpose:
          "Indiquer la part des demandes injectées qui a été traitée.",
        source: "40_FMS / Traitement FMS",
        calculation: [
          "KPI = SUM(demandes_traitees) / SUM(demandes_injectees)",
        ],
        note: "Le taux est vide si aucune demande n'a été injectée.",
      },
      {
        name: "Doute confirmé",
        purpose:
          "Suivre les demandes traitées pour lesquelles le doute est confirmé.",
        source: "40_FMS / Traitement FMS",
        calculation: [
          "Valeur = SUM(doute_confirme)",
          "Pourcentage = SUM(doute_confirme) / SUM(demandes_traitees)",
        ],
      },
      {
        name: "Doute levé",
        purpose:
          "Suivre les demandes traitées pour lesquelles le doute a été levé.",
        source: "40_FMS / Traitement FMS",
        calculation: [
          "Valeur = SUM(doute_leve)",
          "Pourcentage = SUM(doute_leve) / SUM(demandes_traitees)",
        ],
      },
    ],
  },
  {
    title: "Fraude et rescoring",
    description:
      "Ces KPI résument les sorties de bénéficiaires dues à la fraude ou au rescoring.",
    items: [
      {
        name: "ASD - ménages radiés",
        purpose:
          "Afficher les ménages ASD radiés pour fraude sur la période sélectionnée.",
        source: "20_ASD / Radiation pour fraude ASD",
        calculation: ["KPI = SUM(radiated_hh_count)"],
        note: "L'alias Excel nb_menages_radies est accepté.",
      },
      {
        name: "AMO Tadamon - ménages radiés",
        purpose:
          "Afficher les ménages AMO Tadamon radiés pour fraude sur la période sélectionnée.",
        source: "30_AMO_Tadamon / Radiation pour fraude AMO Tadamon",
        calculation: ["KPI = SUM(radiated_hh_count)"],
        note: "L'alias Excel nb_menages_radies est accepté.",
      },
      {
        name: "Total ménages radiés",
        purpose:
          "Donner le total national des ménages radiés pour fraude, tous programmes confondus.",
        source: "20_ASD et 30_AMO_Tadamon / Radiation pour fraude",
        calculation: [
          "KPI = SUM(ASD.radiated_hh_count) + SUM(AMO_TADAMON.radiated_hh_count)",
        ],
      },
      {
        name: "Total personnes radiées",
        purpose:
          "Donner le total des personnes associées aux ménages radiés pour fraude.",
        source: "20_ASD et 30_AMO_Tadamon / Radiation pour fraude",
        calculation: [
          "KPI = SUM(ASD.radiated_persons) + SUM(AMO_TADAMON.radiated_persons)",
        ],
        note: "L'alias Excel nb_personnes_radiees est accepté.",
      },
      {
        name: "ASD - ménages sortants rescoring",
        purpose:
          "Afficher les ménages ASD sortis après rescoring sur la période sélectionnée.",
        source: "20_ASD / Rescoring ASD",
        calculation: ["KPI = SUM(nb_sortants_menages)"],
      },
      {
        name: "AMO Tadamon - ménages sortants rescoring",
        purpose:
          "Afficher les ménages AMO Tadamon sortis après rescoring sur la période sélectionnée.",
        source: "30_AMO_Tadamon / Rescoring AMO Tadamon",
        calculation: ["KPI = SUM(nb_sortants_menages)"],
      },
      {
        name: "Ménages non communiqués",
        purpose:
          "Identifier les ménages sortants du rescoring qui ne sont pas encore communiqués.",
        source: "20_ASD et 30_AMO_Tadamon / Rescoring",
        calculation: [
          "KPI = SUM(ASD.nb_menages_non_communiques) + SUM(AMO_TADAMON.nb_menages_non_communiques)",
        ],
      },
    ],
  },
  {
    title: "Economie budgétaire",
    description:
      "Ces KPI estiment l'impact annuel des radiations et sorties de bénéficiaires.",
    items: [
      {
        name: "Economie budgétaire - Fraude",
        purpose:
          "Estimer l'économie annuelle liée aux radiations pour fraude ASD et AMO Tadamon.",
        source: "Radiation pour fraude ASD/AMO Tadamon + 50_Regles_Montant si nécessaire",
        calculation: [
          "Si montant_mensuel_arrete_dh est fourni: annual_saving_row = montant_mensuel_arrete_dh * 12",
          "Sinon: annual_saving_row = radiated_hh_count * montant_mensuel_dh * facteur_annualisation",
          "KPI = SUM(annual_saving_row)",
        ],
      },
      {
        name: "Economie budgétaire - Rescoring",
        purpose:
          "Estimer l'économie annuelle liée aux sorties de ménages après rescoring.",
        source: "Rescoring ASD/AMO Tadamon + 50_Regles_Montant si nécessaire",
        calculation: [
          "Si montant_mensuel_arrete_dh est fourni: annual_saving_row = montant_mensuel_arrete_dh * 12",
          "Sinon: annual_saving_row = nb_sortants_menages * montant_mensuel_dh * facteur_annualisation",
          "KPI = SUM(annual_saving_row)",
        ],
      },
      {
        name: "Economie budgétaire totale",
        purpose:
          "Afficher l'économie annuelle totale estimée sur le dashboard.",
        source: "KPI économie fraude + KPI économie rescoring",
        calculation: [
          "KPI = Economie budgétaire - Fraude + Economie budgétaire - Rescoring",
        ],
      },
    ],
  },
];

const visualSections: MethodologySection[] = [
  {
    title: "Graphiques et tableaux",
    description:
      "Les graphiques utilisent les mêmes données que les KPI, puis les agrègent par mois, région, province ou famille de risque.",
    items: [
      {
        name: "Dynamique des inscriptions au RNP",
        purpose:
          "Visualiser l'évolution mensuelle des nouvelles inscriptions individuelles RNP.",
        source: "11_RNP_Nouvelles_Inscriptions",
        calculation: [
          "Grouper par mois_evenement",
          "Utiliser type_unite = PERSONNES si la colonne est absente",
          "Valeur mensuelle = SUM(nb_nouvelles_inscriptions)",
        ],
        note: "Le dashboard peut encore lire l'ancien nom de feuille 11_RSU_Nouvelles_Inscriptions pour compatibilité.",
      },
      {
        name: "Ligne de tendance RNP",
        purpose:
          "Donner une lecture rapide de l'orientation des inscriptions RNP.",
        source: "Série mensuelle RNP",
        calculation: [
          "REGRESSION_LINEAIRE = régression sur les valeurs mensuelles",
          "MOYENNE_MOBILE = moyenne mobile sur 3 mois",
          "AUCUNE = pas de ligne de tendance",
        ],
      },
      {
        name: "Dynamique d'entrées / sorties ASD",
        purpose:
          "Comparer les entrées, sorties et le solde net ASD par mois.",
        source: "20_ASD / Flux entrants/sortants ASD",
        calculation: [
          "entrants = SUM(nb_entrants_menages)",
          "sortants = SUM(nb_sortants_menages)",
          "net = entrants - sortants",
        ],
      },
      {
        name: "Matrice FMS par famille et niveau de risque",
        purpose:
          "Comparer les résultats FMS selon le type de famille et le niveau de risque.",
        source: "40_FMS / Traitement FMS",
        calculation: [
          "Grouper par code_type_famille et code_niveau_risque",
          "demandes_traitees = SUM(demandes_traitees)",
          "doute_confirme_pct = SUM(doute_confirme) / SUM(demandes_traitees)",
          "doute_leve_pct = SUM(doute_leve) / SUM(demandes_traitees)",
        ],
      },
      {
        name: "Ménages bloqués - National",
        purpose:
          "Identifier les principaux motifs de blocage des ménages.",
        source: "40_FMS / Ménages bloqués",
        calculation: [
          "Grouper par code_motif_blocage",
          "menages_bloques = SUM(nb_menages_bloques)",
          "personnes_bloquees = SUM(nb_personnes_bloquees)",
        ],
        note: "Les lignes sont triées par menages_bloques décroissant.",
      },
      {
        name: "Entrants / sortants ASD + AMO Tadamon par région",
        purpose:
          "Comparer les flux régionaux des deux programmes sur le mois courant.",
        source: "20_ASD et 30_AMO_Tadamon / Flux entrants/sortants",
        calculation: [
          "Filtrer mois_evenement = mois_reporting_courant",
          "entrants = SUM(ASD.nb_entrants_menages) + SUM(AMO_TADAMON.nb_entrants_menages)",
          "sortants = SUM(ASD.nb_sortants_menages) + SUM(AMO_TADAMON.nb_sortants_menages)",
          "net = entrants - sortants",
        ],
      },
      {
        name: "Top 5 provinces - flux net",
        purpose:
          "Montrer les provinces avec le plus fort solde net d'entrées.",
        source: "20_ASD et 30_AMO_Tadamon / Flux entrants/sortants",
        calculation: [
          "Grouper par nom_province",
          "net = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)",
          "Afficher les 5 premières provinces triées par net décroissant",
        ],
      },
      {
        name: "Ménages bloqués par région",
        purpose:
          "Montrer la répartition régionale des ménages bloqués.",
        source: "40_FMS / Ménages bloqués",
        calculation: [
          "Grouper par code_region",
          "menages_bloques = SUM(nb_menages_bloques)",
        ],
      },
      {
        name: "Top 5 provinces - ménages bloqués",
        purpose:
          "Identifier les provinces qui concentrent le plus de ménages bloqués.",
        source: "40_FMS / Ménages bloqués",
        calculation: [
          "Grouper par nom_province",
          "menages_bloques = SUM(nb_menages_bloques)",
          "Afficher les 5 premières provinces triées par menages_bloques décroissant",
        ],
      },
    ],
  },
];

export default function KpiMethodologyPage(): React.ReactElement {
  return (
    <div className="space-y-6">
      <header className="space-y-4">
        <Link
          href="/dashboard/macro-national"
          className="inline-flex items-center gap-2 text-sm font-medium text-brand-muted hover:text-brand-dark"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Retour au dashboard Macro National
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-brand-primary">
              <BookOpen className="h-5 w-5" aria-hidden />
              <span className="text-sm font-semibold uppercase">
                Méthodologie
              </span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-brand-dark">
              Calcul des KPI du dashboard
            </h1>
            <p className="mt-2 text-sm leading-6 text-brand-muted">
              Cette page explique ce que chaque indicateur mesure, les données
              Excel utilisées et la règle de calcul appliquée dans le dashboard
              Macro National.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-slate-700">
            <span className="inline-flex items-center gap-2 rounded-md border border-brand-border bg-white px-3 py-2">
              <Database className="h-4 w-4 text-brand-primary" aria-hidden />
              Données validées uniquement
            </span>
            <span className="inline-flex items-center gap-2 rounded-md border border-brand-border bg-white px-3 py-2">
              <Calculator className="h-4 w-4 text-brand-primary" aria-hidden />
              Agrégations nationales
            </span>
          </div>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-3">
        {scopeRules.map((rule) => (
          <div
            key={rule.title}
            className="rounded-lg border border-brand-border bg-white p-4 shadow-card"
          >
            <h2 className="text-sm font-semibold text-brand-dark">
              {rule.title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-brand-muted">
              {rule.body}
            </p>
          </div>
        ))}
      </section>

      {kpiSections.map((section) => (
        <MethodologySectionView
          key={section.title}
          section={section}
          icon={<Calculator className="h-5 w-5" aria-hidden />}
        />
      ))}

      {visualSections.map((section) => (
        <MethodologySectionView
          key={section.title}
          section={section}
          icon={<LineChart className="h-5 w-5" aria-hidden />}
        />
      ))}

      <section className="rounded-lg border border-brand-border bg-white p-5 shadow-card">
        <div className="flex items-start gap-3">
          <TableProperties className="mt-0.5 h-5 w-5 text-brand-primary" aria-hidden />
          <div>
            <h2 className="text-base font-semibold text-brand-dark">
              Annotations et notes
            </h2>
            <p className="mt-2 text-sm leading-6 text-brand-muted">
              Les annotations RSU sont gérées dans l&apos;application. Le dashboard
              ajoute aussi une note si le rescoring ASD ou AMO Tadamon contient
              des ménages non communiqués.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

function MethodologySectionView({
  section,
  icon,
}: {
  section: MethodologySection;
  icon: React.ReactNode;
}): React.ReactElement {
  return (
    <section className="space-y-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-brand-primary">{icon}</span>
        <div>
          <h2 className="text-lg font-semibold text-brand-dark">
            {section.title}
          </h2>
          <p className="mt-1 text-sm leading-6 text-brand-muted">
            {section.description}
          </p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        {section.items.map((item) => (
          <MethodologyCard key={item.name} item={item} />
        ))}
      </div>
    </section>
  );
}

function MethodologyCard({
  item,
}: {
  item: MethodologyItem;
}): React.ReactElement {
  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle className="text-base">{item.name}</CardTitle>
        <CardDescription>{item.purpose}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4 text-sm">
        <div>
          <p className="text-xs font-semibold uppercase text-brand-muted">
            Source
          </p>
          <p className="mt-1 rounded-md bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800">
            {item.source}
          </p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase text-brand-muted">
            Calcul
          </p>
          <div className="mt-1 overflow-x-auto rounded-md bg-slate-950 px-3 py-2 font-mono text-xs leading-5 text-slate-50">
            {item.calculation.map((line) => (
              <p key={line} className="whitespace-pre-wrap">
                {line}
              </p>
            ))}
          </div>
        </div>

        {item.note ? (
          <p className="mt-auto rounded-md border border-brand-border bg-slate-50 px-3 py-2 text-xs leading-5 text-brand-muted">
            {item.note}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
