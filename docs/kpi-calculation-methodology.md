# RSU Dashboard KPI Calculation Methodology

This document explains how each dashboard KPI, chart, and summary table is calculated from the uploaded Excel workbook.

Related input schema: `docs/report-excel-upload-schema.md`.

## Global Calculation Rules

### Date Scope

The dashboard is built from the selected date range in the app.

- Flow/event sections use rows where internal `date_evenement` is inside the selected range.
  For simplified client uploads, the app derives `date_evenement` from `fin_periode`.
- Stock/snapshot sections use the latest available snapshot for `date_reference` in the selected range.
- If no dashboard data exists for the selected range, the app returns “Aucune donnée disponible pour le moment”.

### Reference Date

The dashboard reference date is:

```text
metadata.date_reference_donnees
```

For snapshot metrics, the calculation selects the latest row with:

```text
date_reference <= date_reference_donnees
```

within the rows available to the dashboard.

### Current Month

The current reporting month is:

```text
metadata.mois_reporting_courant
```

If it is missing, the dashboard uses the latest `mois_evenement` found in flow/fraud/rescoring data.

### Previous Month

The previous month is:

- the previous available month in the data, if `mois_reporting_courant` exists in the available months;
- otherwise the calendar month before `mois_reporting_courant`.

### Percentages

All percentages use:

```text
numerator / denominator
```

If the denominator is `0`, the percentage is blank.

## KPI Cards

### RNP - personnes cumulées

Source: `11_RNP_Nouvelles_Inscriptions`

Filter:

```text
code_registre = RNP
type_unite = PERSONNES
date_evenement in selected dashboard range
```

Formula:

```text
RNP personnes cumulées = SUM(nb_nouvelles_inscriptions)
```

### RSU - ménages cumulés

Source: `12_RSU_Nouvelles_Inscriptions`

Filter:

```text
code_registre = RSU
type_unite = MENAGES
date_evenement in selected dashboard range
```

Formula:

```text
RSU ménages cumulés = SUM(nb_nouvelles_inscriptions)
```

### RSU - personnes couvertes

Source: `10_RSU` / `Stock RNP/RSU`

If this stock section is not supplied, the KPI is unavailable rather than `0`.

Filter:

```text
code_registre = RSU
type_unite = PERSONNES
latest date_reference <= date_reference_donnees
```

Formula:

```text
RSU personnes = total_cumule
```

This metric is optional context. The main RSU cumulative KPI is `RSU` / `MENAGES`
because RSU is household/family-level in the client data model.

### Nouvelles inscriptions RNP

Source: `11_RNP_Nouvelles_Inscriptions`

Filter:

```text
type_unite = PERSONNES
mois_evenement = mois_reporting_courant
```

Default unit if the column is omitted:

```text
PERSONNES
```

Formula:

```text
Nouvelles inscriptions = SUM(nb_nouvelles_inscriptions)
```

### Evolution vs mois précédent

Source: monthly RNP new registrations.

Formula:

```text
delta = inscriptions_mois_courant - inscriptions_mois_precedent
delta_pct = delta / inscriptions_mois_precedent
```

If `inscriptions_mois_precedent = 0`, `delta_pct` is blank.

### ASD - ménages net cumulés

Source: `21_ASD_Flux`

Filter:

```text
date_evenement in selected dashboard range
```

Formula:

```text
ASD ménages net cumulés = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)
```

The uploaded client extracts track ASD at household level. Person-level ASD KPI
cards are not displayed.

### AMO Tadamon - ménages net cumulés

Source: `31_AMO_Tadamon_Flux`

Filter:

```text
date_evenement in selected dashboard range
```

Formula:

```text
AMO Tadamon ménages net cumulés = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)
```

The uploaded client extracts track AMO Tadamon at household level. Person-level
AMO Tadamon KPI cards are not displayed.

### Demandes injectées FMS

Source: `40_FMS` / `Traitement FMS`

Filter:

```text
date_evenement in selected dashboard range
```

Formula:

```text
Demandes injectées = SUM(demandes_injectees)
```

### Demandes traitées FMS

Source: `40_FMS` / `Traitement FMS`

Formula:

```text
Demandes traitées = SUM(demandes_traitees)
```

### Taux de traitement FMS

Source: `40_FMS` / `Traitement FMS`

Formula:

```text
Taux de traitement = SUM(demandes_traitees) / SUM(demandes_injectees)
```

### Doute confirmé

Source: `40_FMS` / `Traitement FMS`

Formula:

```text
Doute confirmé = SUM(doute_confirme)
Doute confirmé % = SUM(doute_confirme) / SUM(demandes_traitees)
```

### Doute levé

Source: `40_FMS` / `Traitement FMS`

Formula:

```text
Doute levé = SUM(doute_leve)
Doute levé % = SUM(doute_leve) / SUM(demandes_traitees)
```

### ASD - ménages radiés

Source: `20_ASD` / `Radiation pour fraude ASD`

Formula:

```text
ASD ménages radiés = SUM(radiated_hh_count)
```

Alias accepted in Excel:

```text
nb_menages_radies
```

### AMO Tadamon - ménages radiés

Source: `30_AMO_Tadamon` / `Radiation pour fraude AMO Tadamon`

Formula:

```text
AMO Tadamon ménages radiés = SUM(radiated_hh_count)
```

Alias accepted in Excel:

```text
nb_menages_radies
```

### Total ménages radiés

Source: fraud rows from ASD and AMO Tadamon.

Formula:

```text
Total ménages radiés =
  SUM(ASD.radiated_hh_count)
  + SUM(AMO_TADAMON.radiated_hh_count)
```

### Total personnes radiées

Source: fraud rows from ASD and AMO Tadamon.

Formula:

```text
Total personnes radiées =
  SUM(ASD.radiated_persons)
  + SUM(AMO_TADAMON.radiated_persons)
```

Alias accepted in Excel:

```text
nb_personnes_radiees
```

### ASD - ménages sortants rescoring

Source: `20_ASD` / `Rescoring ASD`

Formula:

```text
ASD ménages sortants = SUM(nb_sortants_menages)
```

### AMO Tadamon - ménages sortants rescoring

Source: `30_AMO_Tadamon` / `Rescoring AMO Tadamon`

Formula:

```text
AMO Tadamon ménages sortants = SUM(nb_sortants_menages)
```

### Ménages non communiqués

Source: rescoring rows from ASD and AMO Tadamon.

Formula:

```text
Ménages non communiqués =
  SUM(ASD.nb_menages_non_communiques)
  + SUM(AMO_TADAMON.nb_menages_non_communiques)
```

### Economie budgétaire - Fraude

Sources:

- `20_ASD` / `Radiation pour fraude ASD`
- `30_AMO_Tadamon` / `Radiation pour fraude AMO Tadamon`
- optional fallback rules from `50_Regles_Montant`

For each fraud row:

If `montant_mensuel_arrete_dh` is present:

```text
annual_saving_row = montant_mensuel_arrete_dh * 12
```

If `montant_mensuel_arrete_dh` is empty, use active amount rule for the program:

```text
annual_saving_row =
  radiated_hh_count
  * montant_mensuel_dh
  * facteur_annualisation
```

Active amount rule:

```text
code_programme matches the program
date_effet_debut <= date_reference_donnees
date_effet_fin is empty OR date_effet_fin >= date_reference_donnees
```

Final formula:

```text
Economie fraude = SUM(annual_saving_row for ASD fraud)
                + SUM(annual_saving_row for AMO Tadamon fraud)
```

### Economie budgétaire - Rescoring

Sources:

- `20_ASD` / `Rescoring ASD`
- `30_AMO_Tadamon` / `Rescoring AMO Tadamon`
- optional fallback rules from `50_Regles_Montant`

For each rescoring row:

If `montant_mensuel_arrete_dh` is present:

```text
annual_saving_row = montant_mensuel_arrete_dh * 12
```

If `montant_mensuel_arrete_dh` is empty, use active amount rule for the program:

```text
annual_saving_row =
  nb_sortants_menages
  * montant_mensuel_dh
  * facteur_annualisation
```

Final formula:

```text
Economie rescoring = SUM(annual_saving_row for ASD rescoring)
                   + SUM(annual_saving_row for AMO Tadamon rescoring)
```

### Economie budgétaire totale

Formula:

```text
Economie budgétaire totale = Economie fraude + Economie rescoring
```

## Charts And Tables

### Dynamique des inscriptions au RNP

Source: `11_RNP_Nouvelles_Inscriptions`

Main monthly formula:

```text
RNP monthly value =
  SUM(nb_nouvelles_inscriptions)
  grouped by mois_evenement
  filtered by type_unite = PERSONNES
```

The legacy sheet name `11_RSU_Nouvelles_Inscriptions` remains accepted for
older files, but new files should use the RNP sheet name.

Monthly evolution table:

```text
delta = month_value - previous_month_value
percent_change = delta / previous_month_value
```

If `metadata.indicateur_mois_partiel = true`, the current month label receives `metadata.suffixe_libelle_mois_partiel`.

### RSU Trend Line

Source: monthly RSU values.

The trend method comes from:

```text
metadata.methode_tendance
```

Supported methods:

- `REGRESSION_LINEAIRE`: linear regression over monthly values.
- `MOYENNE_MOBILE`: moving average with a 3-month window.
- `AUCUNE`: no trend line.

### Dynamique d’entrées / sorties ASD

Source: `20_ASD` / `Flux entrants/sortants ASD`

Formula by `mois_evenement`:

```text
entrants = SUM(nb_entrants_menages)
sortants = SUM(nb_sortants_menages)
net = entrants - sortants
```

The comparison table displays the previous month and current month.

### FMS Matrix By Family And Risk Level

Source: `40_FMS` / `Traitement FMS`

Grouped by:

```text
type_famille, normalized internally as code_type_famille
niveau_risque, normalized internally as code_niveau_risque
```

Formulas:

```text
demandes_injectees = SUM(demandes_injectees)
demandes_traitees = SUM(demandes_traitees)
doute_confirme = SUM(doute_confirme)
doute_confirme_pct = SUM(doute_confirme) / SUM(demandes_traitees)
doute_leve = SUM(doute_leve)
doute_leve_pct = SUM(doute_leve) / SUM(demandes_traitees)
```

Labels are taken from `04_Codes`.

### Ménages bloqués - National

Source: `40_FMS` / `Ménages bloqués`

Grouped by:

```text
motif_blocage, normalized internally as code_motif_blocage
```

Formulas:

```text
menages_bloques = SUM(nb_menages_bloques)
personnes_bloquees = SUM(nb_personnes_bloquees)
```

Rows are sorted by `menages_bloques` descending. Labels are taken from `04_Codes`.

### Entrants / Sortants ASD + AMO Tadamon By Region

Sources:

- `20_ASD` / `Flux entrants/sortants ASD`
- `30_AMO_Tadamon` / `Flux entrants/sortants AMO Tadamon`

Filter:

```text
mois_evenement = mois_reporting_courant
```

Grouped by:

```text
code_region
```

Formulas:

```text
entrants = SUM(ASD.nb_entrants_menages) + SUM(AMO_TADAMON.nb_entrants_menages)
sortants = SUM(ASD.nb_sortants_menages) + SUM(AMO_TADAMON.nb_sortants_menages)
net = entrants - sortants
```

Regions follow the order from `02_Regions.ordre_affichage`.

### Top 5 Provinces - Flux Net

Sources:

- `20_ASD` / `Flux entrants/sortants ASD`
- `30_AMO_Tadamon` / `Flux entrants/sortants AMO Tadamon`

Filter:

```text
mois_evenement = mois_reporting_courant
```

Grouped by:

```text
nom_province
```

Formula:

```text
net = SUM(nb_entrants_menages) - SUM(nb_sortants_menages)
```

The table shows the top 5 provinces sorted by `net` descending.

### Ménages bloqués By Region

Source: `40_FMS` / `Ménages bloqués`

Grouped by:

```text
code_region
```

Formula:

```text
menages_bloques = SUM(nb_menages_bloques)
```

Regions follow the order from `02_Regions.ordre_affichage`.

### Top 5 Provinces - Ménages bloqués

Source: `40_FMS` / `Ménages bloqués`

Grouped by:

```text
nom_province
```

Formula:

```text
menages_bloques = SUM(nb_menages_bloques)
```

The table shows the top 5 provinces sorted by `menages_bloques` descending.

## Footnotes

Footnotes include:

1. App-managed RSU annotation labels where `libelle_annotation` is present.
2. If ASD rescoring has `nb_menages_non_communiques > 0`, the dashboard adds an ASD non-communicated households note.
3. If AMO Tadamon rescoring has `nb_menages_non_communiques > 0`, the dashboard adds an AMO Tadamon non-communicated households note.
