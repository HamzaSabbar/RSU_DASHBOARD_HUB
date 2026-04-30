# RSU Dashboard Excel Upload Schema

This document describes the Excel workbook expected by the RSU dashboard upload.
The client can generate this workbook from their databases, then upload it in the app.

The client workbook should contain only report parameters and KPI fact data. Stable
reference data such as regions, provinces, code lists, amount rules, display defaults,
and upload IDs are owned by the application.

## General Rules

- File format: `.xlsx`
- Sheet names must match exactly.
- Each required sheet contains one table. A normal column header row is required.
- No separate title row is required.
- Data rows should be directly below the column header row.
- Column names should match the names below. Unknown columns are accepted with a validation warning; missing required columns fail validation.
- In the tables below, `Required` means the column header is required. Some values can be empty only where the notes explicitly say so.
- Dates may be Excel dates or text in `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`, or `YYYY/MM/DD`.
- Month fields must use `YYYY-MM`.
- Numeric values must be non-negative.
- Do not include `id_chargement` columns in the client workbook. The application generates an internal upload/batch ID when the workbook is uploaded.
- `code_region` values must exist in the application region catalog.
- `nom_province` values must exist in the application province catalog and must belong to the provided `code_region`.
- Code fields are validated against the application code catalog.

## Required Sheets

- `01_Parametres`
- `10_RSU_Stock`
- `11_RSU_Nouvelles_Inscriptions`
- `20_ASD_Stock`
- `21_ASD_Flux`
- `22_ASD_Rescoring`
- `23_ASD_Fraude`
- `30_AMO_Tadamon_Stock`
- `31_AMO_Tadamon_Flux`
- `32_AMO_Tadamon_Rescoring`
- `33_AMO_Tadamon_Fraude`
- `40_FMS_Traitement`
- `41_FMS_Menages_Bloques`

## Optional Sheets

- `00_Guide`
- `12_RSU_Annotations`

## System-Owned References

These references should be configured in the application and should not be requested
from the client in every upload.

| Reference | Owned by the app | Used for |
|---|---|---|
| Regions | `code_region`, `nom_region`, display order | Validate and label all regional rows. |
| Provinces | `code_region`, `nom_province`, display order | Validate province names and region/province consistency. |
| Code lists | Registers, units, source modes, trend methods, family types, risk levels, program perimeters, block reasons, programs, amount types | Validate coded fields and keep labels stable. |
| Amount rules | Program, effective dates, family type, beneficiary unit, amount type, monthly amount, annualization factor | Compute savings when fraud/rescoring rows omit `montant_mensuel_arrete_dh`. |
| Upload metadata | Internal upload ID, uploader, language, chart unit, trend method, fallback behavior | Keep operational metadata consistent without client extraction logic. |

Recommended minimum code families in the application code catalog:

| type_code | Example values |
|---|---|
| `code_registre` | `RNP`, `RSU` |
| `type_unite` | `MENAGES`, `PERSONNES` |
| `mode_source` | `SAISIE`, `DIFF_SNAPSHOT_CUMULE` |
| `methode_tendance` | `REGRESSION_LINEAIRE`, `MOYENNE_MOBILE`, `AUCUNE` |
| `code_type_famille` | Client/domain-defined family or risk population codes, for example `T1`, `T2`. |
| `code_niveau_risque` | Client/domain-defined risk levels, for example `ELEVE`, `MOYEN`, `FAIBLE`. |
| `code_perimetre_programme` | `ASD`, `AMO_TADAMON` |
| `code_motif_blocage` | Client/domain-defined block reasons, for example `FMS`, `MULTI`, `INDIV`. |
| `code_programme` | `ASD`, `AMO_TADAMON` |
| `unite_beneficiaire` | Usually `MENAGES`. |
| `type_montant` | Usually `STANDARD`, or another configured amount type. |

## 01_Parametres

Must contain exactly one active row of report parameters.

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `version_fichier` | text | yes | Template/source version. |
| `date_rapport` | date | yes | Report publication date. |
| `debut_periode` | date | yes | Reporting period start. |
| `fin_periode` | date | yes | Reporting period end. |
| `date_reference_donnees` | date | yes | Snapshot/reference date for stock data. |
| `date_heure_extraction` | datetime | yes | Data extraction timestamp. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | no | Optional free text. |

The app supplies defaults for language, current reporting month, RSU chart unit,
trend method, fallback amount behavior, uploader, and internal upload ID.

## 10_RSU_Stock

Required stock combinations:

- `RNP` / `PERSONNES`
- `RSU` / `MENAGES`
- `RSU` / `PERSONNES`

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `date_reference` | date | yes | Snapshot date. |
| `code_registre` | code | yes | `RNP` or `RSU`. |
| `type_unite` | code | yes | `MENAGES` or `PERSONNES`. |
| `total_cumule` | integer | yes | Cumulative total. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 11_RSU_Nouvelles_Inscriptions

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `debut_periode` | date | yes | Event period start. |
| `fin_periode` | date | yes | Event period end. |
| `date_evenement` | date | yes | Event date used by dashboard date filter. |
| `mois_evenement` | month | yes | Format `YYYY-MM`. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `type_unite` | code | yes | `MENAGES` or `PERSONNES`. |
| `nb_nouvelles_inscriptions` | integer | yes | Count of new registrations. |
| `mode_source` | code | yes | Must exist in the app code catalog. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 12_RSU_Annotations

Optional chart annotations.

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `code_graphique` | text | yes | Chart identifier, for example `RSU`. |
| `mois_evenement` | month | yes | Format `YYYY-MM`. |
| `libelle_annotation` | text | yes | Text displayed/kept as annotation. |
| `commentaires` | text | yes | Can be empty. |

## 20_ASD_Stock

Required stock combinations:

- `MENAGES`
- `PERSONNES`

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `date_reference` | date | yes | Snapshot date. |
| `type_unite` | code | yes | `MENAGES` or `PERSONNES`. |
| `nb_actifs` | integer | yes | Active beneficiaries. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 21_ASD_Flux

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `debut_periode` | date | yes | Event period start. |
| `fin_periode` | date | yes | Event period end. |
| `date_evenement` | date | yes | Event date used by dashboard date filter. |
| `mois_evenement` | month | yes | Format `YYYY-MM`. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `nb_entrants_menages` | integer | yes | Entering households. |
| `nb_sortants_menages` | integer | yes | Exiting households. |
| `nb_entrants_personnes` | integer | yes | Entering persons. |
| `nb_sortants_personnes` | integer | yes | Exiting persons. |
| `montant_mensuel_entrants_dh` | decimal | yes | Monthly amount for entrants in DH. |
| `montant_mensuel_sortants_dh` | decimal | yes | Monthly amount stopped for exits in DH. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 22_ASD_Rescoring

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `debut_periode` | date | yes | Event period start. |
| `fin_periode` | date | yes | Event period end. |
| `date_evenement` | date | yes | Event date used by dashboard date filter. |
| `mois_evenement` | month | yes | Format `YYYY-MM`. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `nb_sortants_menages` | integer | yes | Households exited by rescoring. |
| `nb_sortants_personnes` | integer | yes | Persons exited by rescoring. |
| `nb_menages_non_communiques` | integer | yes | Households not communicated. |
| `montant_mensuel_arrete_dh` | decimal | no | If empty, the app uses configured amount rules for `ASD`. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 23_ASD_Fraude

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `debut_periode` | date | yes | Event period start. |
| `fin_periode` | date | yes | Event period end. |
| `date_evenement` | date | yes | Event date used by dashboard date filter. |
| `mois_evenement` | month | yes | Format `YYYY-MM`. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `radiated_hh_count` | integer | yes | Alias accepted: `nb_menages_radies`. |
| `radiated_persons` | integer | yes | Alias accepted: `nb_personnes_radiees`. |
| `montant_mensuel_arrete_dh` | decimal | no | If empty, the app uses configured amount rules for `ASD`. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 30_AMO_Tadamon_Stock

AMO Tadamon stock data.

Same columns as `20_ASD_Stock`.

Required stock combinations:

- `MENAGES`
- `PERSONNES`

## 31_AMO_Tadamon_Flux

Same columns as `21_ASD_Flux`.

## 32_AMO_Tadamon_Rescoring

Same columns as `22_ASD_Rescoring`. If `montant_mensuel_arrete_dh` is empty,
the app uses configured amount rules for `AMO_TADAMON`.

## 33_AMO_Tadamon_Fraude

Same columns as `23_ASD_Fraude`. If `montant_mensuel_arrete_dh` is empty,
the app uses configured amount rules for `AMO_TADAMON`.

## 40_FMS_Traitement

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `date_reference` | date | yes | Snapshot date. |
| `code_type_famille` | code | yes | Must exist in the app code catalog. |
| `code_niveau_risque` | code | yes | Must exist in the app code catalog. |
| `code_perimetre_programme` | code | yes | Usually `ASD` or `AMO_TADAMON`. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `demandes_injectees` | integer | yes | Requests injected into FMS. |
| `demandes_traitees` | integer | yes | Must not exceed `demandes_injectees`. |
| `doute_confirme` | integer | yes | `doute_confirme + doute_leve` must not exceed `demandes_traitees`. |
| `doute_leve` | integer | yes | Cleared suspicions. |
| `en_attente` | integer | yes | Should equal `demandes_injectees - demandes_traitees` within 1%. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## 41_FMS_Menages_Bloques

| Column | Type | Required | Notes |
|---|---:|---:|---|
| `date_reference` | date | yes | Snapshot date. |
| `code_motif_blocage` | code | yes | Must exist in the app code catalog. |
| `code_type_famille` | code | yes | Must exist in the app code catalog. |
| `code_region` | text | yes | Must exist in the app region catalog. |
| `nom_province` | text | yes | Must exist in the app province catalog. |
| `nb_menages_bloques` | integer | yes | Blocked households. |
| `nb_personnes_bloquees` | integer | yes | Blocked persons. |
| `systeme_source` | text | yes | Source system. |
| `commentaires` | text | yes | Can be empty. |

## Recommended Client Extraction Granularity

- Stock sheets should contain one row per reference date, unit, and relevant code.
- Flow sheets should contain one row per event date, month, region, province, and program/unit.
- FMS sheets should contain one row per reference date, family type, risk level, program perimeter, region, and province.
- All rows in one workbook should represent one coherent reporting extraction.

## Minimal Workbook Skeleton

For each sheet, create:

1. One header row with the exact columns listed above.
2. Data rows directly below that header.
3. Optional blank rows after the table are accepted.

## Backward Compatibility

The parser still accepts older workbooks that include reference/configuration sheets
or grouped fact sheets:

- Legacy reference/configuration sheets: `02_Regions`, `03_Provinces`, `04_Codes`, `50_Regles_Montant`
- Legacy grouped fact sheets: `10_RSU`, `20_ASD`, `30_AMO_Tadamon`, `40_FMS`

For new client extracts, use the simplified one-table-per-sheet layout above and
manage references in the application.
