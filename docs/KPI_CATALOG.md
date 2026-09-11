# KPI Catalog — 18 RSU Process KPIs

## Global statistical rules

### Ratio KPIs
Never average row-level percentages.

For any selected filter scope:
`KPI = SUM(numerator) / SUM(denominator)`

### Average-delay KPIs
If source rows contain an average and an associated count:
`weighted_mean = SUM(count_i * mean_i) / SUM(count_i)`

### Percentiles
Never average:
- medians;
- P75;
- P90.

A percentile at a wider aggregation level cannot generally be reconstructed from subgroup percentiles.

For INS-02 and MAJ-01:
- use the workbook-provided national summary for national median/P75/P90;
- for filter combinations without a true precomputed percentile at that exact grain, mark the aggregate percentile unavailable rather than inventing it.

### Stock/evolution KPIs
For each time series:
- `delta_abs_M = value_M - value_M-1`
- `delta_pct_M = (value_M - value_M-1) / value_M-1`
- if previous value is 0, `delta_pct = null`.

---

## ACC-01 — Taux de conversion de l’enrôlement RNP vers la présence au RSU

30j:
`SUM(present_rsu_30j) / SUM(rnp_idcs_actif)`

90j:
`SUM(present_rsu_90j) / SUM(rnp_idcs_actif)`

Dimensions:
- mois d’enrôlement
- région
- province/préfecture
- milieu
- tranche d’âge

---

## INS-01 — Taux d’aboutissement du parcours d’inscription à 30, 60 et 90 jours

30j:
`SUM(finalisees_30j) / SUM(demandes_initiees)`

60j:
`SUM(finalisees_60j) / SUM(demandes_initiees)`

90j:
`SUM(finalisees_90j) / SUM(demandes_initiees)`

Dimensions:
- mois de création
- région
- province/préfecture
- milieu
- canal

---

## INS-02 — Délai de bout en bout de l’inscription RSU

Underlying definition:
`Di = date_inscription_active - date_depot`

Metrics:
- médiane
- P75
- P90

Dimensions in main table:
- mois de dépôt
- région
- province/préfecture
- milieu
- canal
- nombre de dossiers finalisés

National values:
use only the explicit national summary table K:N.

Do not aggregate subgroup percentiles.

---

## INS-03 — Taux d’incohérence des données entre le RNP et le RSU

Global:
`SUM(personnes_avec_incoherence) / SUM(personnes_comparees)`

Dimensions:
- trimestre
- région
- province/préfecture
- milieu

Field analysis adds:
- champ contrôlé
- type d’incohérence

Use the dedicated global table for the global KPI. Do not sum field-level incoherence counts to reconstruct distinct global persons.

---

## FSC-01 — Délai de réponse utilisable par source administrative

Underlying:
`Di = t_reponse_utilisable - t_envoi_initial`

Source metrics:
- délai moyen
- délai médian
- P90

Dimensions:
- mois
- source administrative
- type de flux
- nombre de requêtes valides envoyées

For the current synthetic perimeter, valid included requests are treated as having usable responses.

When aggregating **mean delay** across rows:
weight by request volume.

Do not reconstruct aggregated median/P90 from row-level medians/P90.

---

## MAJ-01 — Délai bout-en-bout mise à jour → nouvel ISE

Underlying:
`Di = date_nouvel_ise - date_initiation_valide`

Metrics:
- médiane
- P75
- P90

Dimensions:
- mois d’initiation
- type de mise à jour
- standard / non standard
- région
- province/préfecture
- milieu
- canal
- nombre de MAJ finalisées
- nombre total de dossiers concernés

National values:
use only explicit national summary N:Q.

Do not aggregate subgroup percentiles.

---

## MAJ-02 — Progression du stock des mises à jour « en cours » par mois

`stock_M = SUM(maj_en_cours at month end)`

`variation_abs = stock_M - stock_M-1`

`variation_pct = variation_abs / stock_M-1` when previous stock > 0.

Dimensions:
- mois/date d’arrêté
- type de mise à jour
- canal
- région
- province/préfecture
- milieu

---

## MAJ-03 — Progression des demandes de mise à jour initiées par les ménages

`volume_M = SUM(demandes_maj_initiees)`

`variation_abs = volume_M - volume_M-1`

`variation_pct = variation_abs / volume_M-1` when previous volume > 0.

Dimensions:
- mois d’initiation
- type de mise à jour
- canal
- région
- province/préfecture
- milieu

---

## MAJ-04 — Taux de ménages non rescorés après une année

`SUM(menages_dernier_rescoring_gt_365j) / SUM(menages_actifs)`

Dimensions:
- date d’arrêté
- région
- province/préfecture
- milieu

---

## NOT-01 — Taux de chefs de ménage avec activité observée (OTP réussi ou notification reçue)

`SUM(chefs_avec_activite_observee) / SUM(chefs_avec_numero_enregistre)`

`chefs_avec_activite_observee` is the workbook's own precomputed union of
"≥1 OTP réussi" and "≥1 notification reçue" — the only valid numerator.
Never compute `chefs_avec_otp_reussi + chefs_avec_notification_recue` as a
substitute: a chef can trigger both events, and a naive sum would
double-count the overlap between the two populations.

Dimensions:
- mois
- région
- province/préfecture
- milieu
- genre
- tranche d’âge

Additional (secondary, explanatory counts — never summed into the ratio):
- chefs avec ≥1 OTP réussi
- chefs avec ≥1 notification reçue

---

## NOT-02 — Taux de livraison du courrier postal

`SUM(courriers_livres) / SUM(courriers_envoyes_observables)`

Dimensions:
- mois d’envoi
- type de courrier
- région
- province/préfecture
- milieu

Additional:
- non livrés/retournés
- encore en acheminement
- motif principal de non-livraison

---

## REC-01 — Délai moyen de traitement des recours

Source row:
- nombre de recours avec décision finale
- délai moyen

Aggregate:
`SUM(nb_decisions_i * delai_moyen_i) / SUM(nb_decisions_i)`

Dimensions:
- mois de dépôt
- motif du recours
- région
- province/préfecture
- milieu

---

## REC-02 — Évolution du stock de recours « en cours »

`stock_M = SUM(recours_en_cours)`

Then monthly absolute and percentage variation.

Dimensions:
- mois
- motif du recours
- région
- province/préfecture

---

## REC-03 — Part des recours acceptés

`SUM(recours_acceptes) / SUM(recours_decision_finale)`

Dimensions:
- mois de décision
- motif du recours
- région
- province/préfecture
- milieu

---

## REC-04 — Délai de traitement des réclamations, Portail / CSC

Source row:
- nombre de réclamations clôturées
- délai moyen
- nombre de réclamations « en cours » (absorbs the retired REC-07's stock concept)

Aggregate (headline delay):
`SUM(nb_cloturees_i * delai_moyen_i) / SUM(nb_cloturees_i)`

Additional (displayed, no headline delta/trend):
- clôturés = `SUM(nb_reclamations_cloturees)` — a flow, safe to sum across any rows/periods.
- en cours = `reclamations_en_cours` read only for the **most recent period** in whatever population is being aggregated — never summed across periods (would double-count an open backlog already counted in an earlier month).

Dimensions:
- mois de dépôt
- canal (Portail / CSC)
- région
- province/préfecture
- milieu

---

## REC-05 — Taux de réclamations rapportées aux préinscriptions + demandes de MAJ du même mois

`SUM(reclamations) / (SUM(preinscriptions) + SUM(demandes_maj))`

Dimensions:
- mois
- région
- province/préfecture
- milieu

Interpretation:
activity-normalization ratio, not a cohort complaint rate.

---

## CQD-01 — Taux de fraudes avérées parmi les suspicions de fraude

Fréquence : mensuelle.

`SUM(fraudes_averees) / SUM(suspicions_cloturees_evaluables)`

Dimensions:
- période
- règle/source de suspicion
- type de fraude suspectée
- région
- province/préfecture
- milieu

Additional:
- suspicions en traitement — dossiers ouverts non encore clôturés, distinct de fraudes avérées / suspicions clôturées.

---

## CQD-02 — Taux de ménages soupçonnés de fraude

Rouge / orange / total are three parallel measures sharing one denominator
(same pattern as ACC-01's 30j/90j) — not a breakdown dimension:

- `SUM(menages_soupconnes_rouge) / SUM(menages_actifs)` (rouge)
- `SUM(menages_soupconnes_orange) / SUM(menages_actifs)` (orange)
- `(SUM(menages_soupconnes_rouge) + SUM(menages_soupconnes_orange)) / SUM(menages_actifs)` (total — the headline value)

"Total" is **derived** as rouge + orange, never read from the workbook's own
"Nombre total de ménages soupçonnés" column — that column is blank on every
row in the real data (rouge/orange are the only counts the source team fills
in). If a future import does populate it, it must agree with rouge + orange
(validated, not required).

Dimensions:
- période
- région
- province/préfecture
- milieu

Each household is distinct within the supplied numerator grain. Rouge and
orange are mutually exclusive categories at the source: a household is
counted under exactly one of them — never derived by summing across a split
dimension.
