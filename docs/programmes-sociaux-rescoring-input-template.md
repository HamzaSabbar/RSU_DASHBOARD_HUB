# Programmes sociaux / Rescoring — modèle de données Excel

> Ce modèle décrit le contrat logique du dashboard. La source de vérité cible
> est désormais le lot CSV RSU commun à tous les dashboards, préparé selon le
> [plan d'architecture data RSU](rsu-data-platform-plan.md). Les feuilles
> ci-dessous correspondent donc aux marts de sortie attendus, pas à une nouvelle
> source indépendante à maintenir manuellement.

## Conclusion

Le fichier Excel du dashboard **Macro National** couvre une grande partie du
dashboard **Programmes sociaux / Rescoring**, mais il n'est pas suffisant à lui
seul.

| Besoin du second dashboard | Couvert par le premier fichier | Source actuelle / manque |
|---|---:|---|
| Filtre programme ASD / AMO Tadamon | Oui | Le programme est déduit des feuilles `21_ASD_Flux` et `31_AMO_Tadamon_Flux`. |
| Filtre région | Oui | `nom_region` est présent dans les feuilles de flux et de rescoring. |
| Filtre province | Oui | `nom_province` est présent dans les feuilles de flux et de rescoring. |
| Période libre | Oui | `date_evenement` permet de filtrer entre une date de début et une date de fin. |
| KPI entrées / sorties | Oui | `nb_entrants_menages` et `nb_sortants_menages`. |
| Courbes ASD / AMO entrées-sorties | Oui | Agrégation des feuilles de flux par semaine, mois ou trimestre. |
| Lecture territoriale | Oui | Agrégation des flux par région ou province. |
| Éligibles avant seuils, par programme | Non | Les inscriptions RSU ne représentent pas l'éligibilité ASD ou AMO Tadamon. |
| Volatilité du scoring ISE | Non | Les feuilles de rescoring ne contiennent ni écart ISE ni tranche d'écart. |

## Modèle recommandé

Le modèle du second dashboard peut rester compact avec une feuille de
paramètres et trois feuilles de faits. Le grain géographique de toutes les
données est la **province**; la région est répétée sur la ligne pour permettre
la validation et le filtrage.

### 00_Guide

Feuille d'instructions. Elle ne contient aucune donnée à importer.

Règles principales:

- codes programme autorisés: `ASD`, `AMO_TADAMON`;
- une ligne ne doit représenter qu'une seule province;
- ne pas mélanger des lignes nationales/régionales et des lignes provinciales;
- nombres entiers positifs ou zéro;
- format de date recommandé: `YYYY-MM-DD`;
- les noms de région et de province sont des libellés métier, pas des codes internes.

### 01_Parametres

Une seule ligne.

| Colonne | Obligatoire | Description |
|---|---:|---|
| `debut_periode` | Oui | Première date couverte par le fichier. |
| `fin_periode` | Oui | Dernière date couverte par le fichier. |
| `date_heure_extraction` | Non | Horodatage de l'extraction. |
| `version_fichier` | Non | Version du format d'extraction. |
| `systeme_source` | Non | Système ayant produit les données. |
| `commentaires` | Non | Note opérationnelle. |

Exemple:

| debut_periode | fin_periode | date_heure_extraction | version_fichier | systeme_source | commentaires |
|---|---|---|---|---|---|
| 2026-01-01 | 2026-03-31 | 2026-04-01 08:30 | rescoring-v1 | SOURCE_PROGRAMMES | Extraction trimestrielle |

### 10_Eligibilite_Programme

Cette feuille est un **snapshot**. Une ligne = une date de référence, un
programme et une province.

| Colonne | Obligatoire | Description |
|---|---:|---|
| `date_reference` | Oui | Date du snapshot d'éligibilité. |
| `code_programme` | Oui | `ASD` ou `AMO_TADAMON`. |
| `nom_region` | Oui | Région de la province. |
| `nom_province` | Oui | Province ou préfecture. |
| `nb_eligibles_avant_seuil` | Oui | Ménages éligibles avant application du seuil du programme. |
| `nb_eligibles_apres_seuil` | Non | Ménages restant éligibles après seuil, si disponible. |
| `version_seuil` | Non | Version/date de la règle de seuil utilisée. |

Exemple:

| date_reference | code_programme | nom_region | nom_province | nb_eligibles_avant_seuil | nb_eligibles_apres_seuil | version_seuil |
|---|---|---|---|---:|---:|---|
| 2026-03-31 | ASD | Casablanca-Settat | Casablanca | 425000 | 386000 | 2026-01 |
| 2026-03-31 | AMO_TADAMON | Casablanca-Settat | Casablanca | 310000 | 282000 | 2026-01 |

Important: les snapshots de plusieurs dates ne sont jamais additionnés. Le
dashboard utilise le dernier `date_reference` inférieur ou égal à la date de
fin choisie.

### 20_Flux_Programme

Une ligne = une date d'événement, un programme et une province. Cette feuille
peut être produite à partir de `21_ASD_Flux` et `31_AMO_Tadamon_Flux` du premier
dashboard en ajoutant `code_programme`.

| Colonne | Obligatoire | Description |
|---|---:|---|
| `date_evenement` | Oui | Jour du mouvement. |
| `code_programme` | Oui | `ASD` ou `AMO_TADAMON`. |
| `nom_region` | Oui | Région de la province. |
| `nom_province` | Oui | Province ou préfecture. |
| `nb_entrants_menages` | Oui | Ménages entrant dans le programme. |
| `nb_sortants_menages` | Oui | Ménages sortant du programme. |
| `nb_entrants_personnes` | Non | Personnes couvertes par les ménages entrants. |
| `nb_sortants_personnes` | Non | Personnes couvertes par les ménages sortants. |

Exemple:

| date_evenement | code_programme | nom_region | nom_province | nb_entrants_menages | nb_sortants_menages | nb_entrants_personnes | nb_sortants_personnes |
|---|---|---|---|---:|---:|---:|---:|
| 2026-03-05 | ASD | Rabat-Salé-Kénitra | Kénitra | 1240 | 980 | 4100 | 3200 |
| 2026-03-05 | AMO_TADAMON | Rabat-Salé-Kénitra | Kénitra | 460 | 180 | 1510 | 590 |

### 30_Volatilite_Scoring

Une ligne = une date, un programme, une province et une tranche d'écart ISE.
Ce format agrégé évite de transmettre des données individuelles.

| Colonne | Obligatoire | Description |
|---|---:|---|
| `date_evenement` | Oui | Date du rescoring ou de la mise à jour. |
| `code_programme` | Oui | `ASD` ou `AMO_TADAMON`. |
| `nom_region` | Oui | Région de la province. |
| `nom_province` | Oui | Province ou préfecture. |
| `tranche_ecart_ise` | Oui | `<1`, `1-5`, `5-10`, `10-20`, `20-30`, `30-50` ou `51+`. |
| `nb_menages_rescores` | Oui | Nombre total de ménages rescorés dans la tranche. |
| `nb_sortants_rescoring` | Oui | Nombre de ménages sortis du programme dans la tranche. |

Exemple:

| date_evenement | code_programme | nom_region | nom_province | tranche_ecart_ise | nb_menages_rescores | nb_sortants_rescoring |
|---|---|---|---|---|---:|---:|
| 2026-03-05 | ASD | Rabat-Salé-Kénitra | Kénitra | <1 | 520 | 110 |
| 2026-03-05 | ASD | Rabat-Salé-Kénitra | Kénitra | 1-5 | 430 | 90 |
| 2026-03-05 | AMO_TADAMON | Rabat-Salé-Kénitra | Kénitra | <1 | 310 | 48 |

## Fonctionnement des filtres

Tous les calculs appliquent les filtres dans cet ordre:

1. **Période:** `date_debut <= date_evenement <= date_fin`.
2. **Programme:** `ASD`, `AMO_TADAMON` ou les deux pour `Tous`.
3. **Région:** toutes les régions ou une région précise.
4. **Province:** toutes les provinces de la région choisie ou une province précise.

La période `Hebdomadaire`, `Mensuel` ou `Trimestriel` change le regroupement de
l'axe du graphique; elle ne remplace pas les dates de début et de fin.

Comportement attendu:

- **Tous:** affiche ASD et AMO Tadamon comme deux séries et additionne les deux
  programmes uniquement dans les indicateurs explicitement nationaux/globaux;
- **ASD:** les KPI, courbes, volatilité et classements utilisent uniquement les
  lignes `code_programme = ASD`;
- **AMO Tadamon:** même logique avec `code_programme = AMO_TADAMON`;
- lorsqu'une région est choisie, la liste des provinces est limitée aux
  provinces de cette région;
- lorsqu'une province est choisie, tous les KPI et graphiques sont recalculés
  pour cette province et la période choisie.

## Calculs du dashboard

| Élément | Calcul après filtres |
|---|---|
| Éligibles avant seuils | Somme de `nb_eligibles_avant_seuil` sur le dernier snapshot disponible. |
| Entrées | Somme de `nb_entrants_menages`. |
| Sorties | Somme de `nb_sortants_menages`. |
| Net | Entrées moins sorties. |
| Courbe entrées/sorties | Sommes regroupées par semaine, mois ou trimestre. |
| Volatilité — part des sorties | `SUM(nb_sortants_rescoring de la tranche) / SUM(nb_sortants_rescoring toutes tranches)`. |
| Lecture territoriale | Net regroupé par région ou province, puis tri décroissant. |

## Clés d'unicité recommandées

- `10_Eligibilite_Programme`: `date_reference + code_programme + nom_province`;
- `20_Flux_Programme`: `date_evenement + code_programme + nom_province`;
- `30_Volatilite_Scoring`: `date_evenement + code_programme + nom_province + tranche_ecart_ise`.

Une clé dupliquée doit bloquer l'import ou être agrégée explicitement par le
système source avant l'envoi.

## Réutilisation du premier fichier

- Copier `21_ASD_Flux` dans `20_Flux_Programme` avec `code_programme = ASD`.
- Copier `31_AMO_Tadamon_Flux` dans `20_Flux_Programme` avec
  `code_programme = AMO_TADAMON`.
- Ne pas utiliser `12_RSU_Nouvelles_Inscriptions` comme éligibilité: inscription
  et éligibilité programme sont deux mesures différentes.
- Les feuilles `22_ASD_Rescoring` et `32_AMO_Tadamon_Rescoring` peuvent fournir
  des totaux de sorties, mais elles ne peuvent pas produire la distribution de
  volatilité sans `tranche_ecart_ise`.

## Écart d'implémentation actuel

La page du second dashboard est encore alimentée par des constantes
illustratives. Son backend ne déclare actuellement aucun fichier attendu et
n'expose pas encore d'endpoint d'import ou d'agrégation. Le modèle ci-dessus
définit le contrat de données à implémenter avant de connecter les filtres et les
graphiques aux données réelles.
