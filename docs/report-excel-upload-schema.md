# RSU Dashboard Excel Upload Schema

This document describes the period-fact Excel workbook expected by the RSU
dashboard upload. The client should send facts for explicit reporting periods.
Stable reference data, cumulative calculations, upload metadata, display
defaults, and internal codes are owned by the application.

The goal of this workbook is to give the dashboard the source period numbers it
cannot compute by itself. The app stores all validated periods and derives
cumulative dashboard values from active uploaded history.

## General Rules

- File format: `.xlsx`
- Sheet names must match exactly.
- Each required sheet contains one table with one normal header row.
- Data rows should be directly below the header row.
- Column names should match the names below.
- Unknown columns are accepted with a validation warning.
- Missing required columns fail validation.
- Numeric values must be non-negative.
- Dates may be Excel dates or text in `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`, or `YYYY/MM/DD`.
- Every fact row should include `debut_periode` and `fin_periode`.
- The first production upload should contain historical period rows from the beginning of available data to the current cut-off date.
- Later uploads should contain only the new weekly period rows.
- The client should not include `id_chargement`, `code_region`, `date_evenement`, `mois_evenement`, stock sheets, RSU annotations, reference sheets, amount rules, or repeated source/comment columns in new workbooks.

## Client Geography Format

The client sends geography names, not region codes.

| Field | Required format | Why needed |
|---|---|---|
| `nom_region` | Region name as text, recommended lowercase ASCII, for example `rabat-sale-kenitra` or `casablanca-settat`. | Used to validate province/region consistency and build regional charts. |
| `nom_province` | Province or prefecture name as text, recommended lowercase ASCII, for example `rabat`, `sale`, `casablanca`, `kenitra`. | Used for province-level rankings and for mapping the row to the app geography catalog. |

Do not send internal codes such as `R01`, `R02`, `CAS`, or `RSK`. The app
normalizes case, accents, spaces, and punctuation, then maps the submitted names
to the application region/province catalog.

Examples accepted by the app:

| Client value | App canonical value |
|---|---|
| `rabat-sale-kenitra` | `Rabat-Salé-Kénitra` |
| `kenitra` | `KÉNITRA` |
| `casablanca-settat` | `Casablanca-Settat` |
| `casablanca` | `CASABLANCA` |

## FMS Classification Format

The client sends business labels, not internal app codes.

| Client field | Required format | Why needed |
|---|---|---|
| `type_famille` | Family/population category label from the FMS source, for example `T1`, `T2`, `TOUS`, `multi noyau`, or the client’s official label. | Needed only because the dashboard shows the FMS matrix by family type. The app cannot infer this from totals such as `demandes_injectees` or `doute_confirme`. |
| `niveau_risque` | Risk level label from the FMS source, for example `eleve`, `moyen`, `faible`. | Needed because the FMS matrix groups treated requests by risk level. The app cannot infer the risk level from the aggregate counts. |
| `motif_blocage` | Blocking reason label from the FMS source, for example `fms`, `multi`, `indiv`. | Needed for the blocked-households breakdown by reason. |

The app normalizes these labels and maps them to its internal code catalog when a
catalog entry exists. If a new valid business label appears, it should be added
to the app catalog, not hard-coded in the client workbook.

`code_perimetre_programme` is not required in the client workbook. The current
dashboard stores this field for legacy uploads, but the current report does not
use it in calculations.

## Dates

The client supplies only the workbook reporting period in `01_Parametres`:

- `debut_periode`
- `fin_periode`

Each fact row supplies its own `debut_periode` and `fin_periode`.
`date_evenement` is not a client field. It is an internal dashboard filtering
date. For client data-only uploads, the app derives:

| Internal field | App derivation | Why needed |
|---|---|---|
| `date_evenement` | From each row's `fin_periode`. | Used internally by the dashboard date-range filter. |
| `mois_evenement` | Month of `fin_periode`, formatted `YYYY-MM`. | Used internally for monthly charts and current-month KPIs. |
| `date_reference` | From `date_reference_donnees` if supplied, otherwise `fin_periode`. | Used internally for legacy stock/snapshot metrics. |

## Required Sheets

- `01_Parametres`
- `11_RNP_Nouvelles_Inscriptions`
- `12_RSU_Nouvelles_Inscriptions`
- `21_ASD_Flux`
- `22_ASD_Rescoring`
- `23_ASD_Fraude`
- `31_AMO_Tadamon_Flux`
- `32_AMO_Tadamon_Rescoring`
- `33_AMO_Tadamon_Fraude`
- `40_FMS_Traitement`
- `41_FMS_Menages_Bloques`

## Optional Sheets

- `00_Guide`
- `10_RSU_Stock`
- `20_ASD_Stock`
- `30_AMO_Tadamon_Stock`

`12_RSU_Annotations` is app-managed. Do not request it from the client in new
uploads.

Stock sheets are legacy/source-dependent. New client uploads should omit them.
The app derives cumulative values from period facts. Do not send placeholder
zero rows to satisfy the dashboard.

## App-Owned Fields

These fields are configured, generated, or normalized by the application:

| App-owned item | App responsibility |
|---|---|
| Regions and provinces | Normalize submitted names, derive `code_region`, validate region/province consistency, and apply display order. |
| Code lists | Validate and label register/unit/FMS/program values. |
| Amount rules | Compute savings when fraud/rescoring rows omit `montant_mensuel_arrete_dh`. |
| Upload metadata | Generate internal upload ID and uploader metadata. |
| Date fields | Derive internal event/month dates from row-level period dates. |
| Cumulative metrics | Sum active period facts over the selected dashboard range. |
| Display defaults | Language, RSU chart unit, trend method, and fallback behavior. |
| RSU annotations | Managed in the app, not in the client upload. |

## 01_Parametres

Must contain exactly one active row.

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Defines the beginning of the reporting period covered by every fact row in the workbook. |
| `fin_periode` | date | yes | Defines the end of the reporting period and is used by the app to derive internal event/month dates. |
| `version_fichier` | text | no | Helps troubleshoot which client template or extraction version produced the file. |
| `date_reference_donnees` | date | no | Lets the app pick the correct stock snapshot date if it differs from `fin_periode`. If empty, the app uses `fin_periode`. |
| `date_heure_extraction` | datetime | no | Helps audit when the source system generated the extract. It does not change KPI calculations. |
| `systeme_source` | text | no | Identifies the source system globally when useful for audit/debugging. |
| `commentaires` | text | no | Optional operational note for the upload. It does not change KPI calculations. |

## 10_RSU_Stock

Legacy optional. New client uploads should not include this sheet.

If included, required stock combinations:

- `RNP` persons
- `RSU` households/families

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `code_registre` | code | yes | Identifies whether the stock value belongs to RNP or RSU. RNP is interpreted as persons; RSU is interpreted as households/families unless `type_unite` is explicitly supplied. |
| `type_unite` | code | no | Optional legacy/unit field. If omitted, the app derives `PERSONNES` for `RNP` and `MENAGES` for `RSU`. Use `RSU` / `PERSONNES` only for optional covered-person context, not as the main RSU stock. |
| `total_cumule` | integer | yes | Source value for the cumulative RNP/RSU stock KPI. |

Do not send `RNP` / `MENAGES`. Do not use an `individus_rsu` source as
`RSU` / `MENAGES`; that source is persons covered by RSU households, not the
number of RSU households/families.

## 11_RNP_Nouvelles_Inscriptions

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `nom_region` | text | yes | Allows the app to map the row to the region catalog for regional validation. |
| `nom_province` | text | yes | Allows province-level aggregation and validation against the region. |
| `type_unite` | code | no | Optional legacy/unit field. If omitted, the app derives `PERSONNES`, because RNP is individual-level. |
| `nb_nouvelles_inscriptions` | integer | yes | Source value for monthly RNP new individual registration KPIs and trend charts. |

The app still accepts the legacy sheet name `11_RSU_Nouvelles_Inscriptions`,
but new workbooks should use `11_RNP_Nouvelles_Inscriptions` so the source is
not mislabeled as RSU family data.

## 12_RSU_Nouvelles_Inscriptions

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `nom_region` | text | yes | Allows the app to map the row to the region catalog for regional validation. |
| `nom_province` | text | yes | Allows province-level aggregation and validation against the region. |
| `nb_nouveaux_menages_rsu` | integer | yes | Source value for RSU household/family registrations during the row period. |

The app derives `code_registre = RSU` and `type_unite = MENAGES`. Do not use
RNP individual registrations or `individus_rsu` as this metric.

## 20_ASD_Stock

Legacy optional. New client uploads should not include this sheet.

If included, required stock combinations:

- `MENAGES`
- `PERSONNES`

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `type_unite` | code | yes | Separates active ASD households from active ASD persons. |
| `nb_actifs` | integer | yes | Source value for ASD active-beneficiary KPI cards. |

## 21_ASD_Flux

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `nom_region` | text | yes | Allows regional ASD/AMO flux aggregation. |
| `nom_province` | text | yes | Allows province-level top flux rankings. |
| `nb_entrants_menages` | integer | yes | Source value for ASD entering-household flow and net flow. |
| `nb_sortants_menages` | integer | yes | Source value for ASD exiting-household flow and net flow. |
| `nb_entrants_personnes` | integer | no | Keeps person-level entering flow available for audit and future person-level views when the source provides it. |
| `nb_sortants_personnes` | integer | no | Keeps person-level exiting flow available for audit and future person-level views when the source provides it. |
| `montant_mensuel_entrants_dh` | decimal | no | Monthly amount added by ASD entrants, used for financial flow views when the source provides it. |
| `montant_mensuel_sortants_dh` | decimal | no | Monthly amount stopped by ASD exits, used for financial flow views when the source provides it. |

## 22_ASD_Rescoring

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `nom_region` | text | yes | Allows rescoring rows to be validated and attributed geographically. |
| `nom_province` | text | yes | Keeps province attribution for rescoring rows. |
| `nb_sortants_menages` | integer | yes | Source value for ASD households exited by rescoring and savings calculation. |
| `nb_sortants_personnes` | integer | yes | Source value for ASD persons exited by rescoring. |
| `nb_menages_non_communiques` | integer | yes | Used for the dashboard footnote about non-communicated households. |
| `montant_mensuel_arrete_dh` | decimal | no | Direct monthly stopped amount. If empty, the app uses configured amount rules for `ASD`. |

## 23_ASD_Fraude

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `nom_region` | text | yes | Allows fraud rows to be validated and attributed geographically. |
| `nom_province` | text | yes | Keeps province attribution for fraud rows. |
| `radiated_hh_count` | integer | yes | Source value for ASD households radiated for fraud and savings calculation. Alias accepted: `nb_menages_radies`. |
| `radiated_persons` | integer | yes | Source value for ASD persons radiated for fraud. Alias accepted: `nb_personnes_radiees`. |
| `montant_mensuel_arrete_dh` | decimal | no | Direct monthly stopped amount. If empty, the app uses configured amount rules for `ASD`. |

## 30_AMO_Tadamon_Stock

Legacy optional. New client uploads should not include this sheet.

Same columns and required stock combinations as `20_ASD_Stock`.

## 31_AMO_Tadamon_Flux

Same columns as `21_ASD_Flux`.

## 32_AMO_Tadamon_Rescoring

Same columns as `22_ASD_Rescoring`. If `montant_mensuel_arrete_dh` is empty,
the app uses configured amount rules for `AMO_TADAMON`.

## 33_AMO_Tadamon_Fraude

Same columns as `23_ASD_Fraude`. If `montant_mensuel_arrete_dh` is empty,
the app uses configured amount rules for `AMO_TADAMON`.

## 40_FMS_Traitement

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `type_famille` | text | yes | Source classification needed to build the FMS matrix by family/population type. The app cannot derive it from aggregate counts. |
| `niveau_risque` | text | yes | Source classification needed to build the FMS matrix by risk level. The app cannot derive it from aggregate counts. |
| `nom_region` | text | yes | Allows regional validation and attribution for FMS treatment rows. |
| `nom_province` | text | yes | Allows province attribution for FMS treatment rows. |
| `demandes_injectees` | integer | yes | Source value for total FMS requests injected. |
| `demandes_traitees` | integer | yes | Source value for total FMS requests processed and processing-rate KPI. |
| `doute_confirme` | integer | yes | Source value for confirmed suspicion counts and rates. |
| `doute_leve` | integer | yes | Source value for cleared suspicion counts and rates. |
| `en_attente` | integer | yes | Source value for pending requests; validated against injected minus processed. |

## 41_FMS_Menages_Bloques

| Column | Type | Required | Why needed |
|---|---:|---:|---|
| `debut_periode` | date | yes | Start date of the period represented by this row. |
| `fin_periode` | date | yes | End date of the period represented by this row. |
| `motif_blocage` | text | yes | Source classification needed for the blocked-households breakdown by blocking reason. |
| `type_famille` | text | yes | Keeps blocked households aligned with the same FMS family/population categories used in treatment rows. |
| `nom_region` | text | yes | Allows regional blocked-household aggregation. |
| `nom_province` | text | yes | Allows top-province blocked-household rankings. |
| `nb_menages_bloques` | integer | yes | Source value for blocked-household KPI and charts. |
| `nb_personnes_bloquees` | integer | no | Source value for blocked-person counts when the source provides it. |

## Recommended Client Extraction Granularity

- Stock sheets should contain one row per unit and relevant register/program code.
- Flow sheets should contain one row per region, province, and unit or metric combination for the workbook period.
- FMS treatment sheets should contain one row per family type, risk level, region, and province for the workbook period.
- FMS blocked sheets should contain one row per blocking reason, family type, region, and province for the workbook period.
- All rows in one workbook should represent one coherent reporting extraction.

## Minimal Workbook Skeleton

For each sheet, create:

1. One header row with the exact columns listed above.
2. Data rows directly below that header.
3. Optional blank rows after the table.

## Backward Compatibility

The parser still accepts older workbooks that include generated/configuration
fields or grouped fact sheets:

- Legacy reference/configuration sheets: `02_Regions`, `03_Provinces`, `04_Codes`, `50_Regles_Montant`
- Legacy grouped fact sheets: `10_RSU`, `20_ASD`, `30_AMO_Tadamon`, `40_FMS`
- Legacy generated columns: `code_region`, `date_reference`, `date_evenement`, `mois_evenement`, `mode_source`, `systeme_source`, `commentaires`
- Legacy FMS code columns: `code_type_famille`, `code_niveau_risque`, `code_motif_blocage`, `code_perimetre_programme`
- Legacy `12_RSU_Annotations`

For new client extracts, use the simplified data-only layout above and manage
references, annotations, dates, and upload metadata in the application.
