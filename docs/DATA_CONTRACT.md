# Data Contract — RSU KPI Multi-Sheet Excel

## Accepted file format

Primary format:
- `.xlsx`
- one workbook may contain all 18 KPI sheets, plus one leading non-data sheet
- baseline seed file:
  `data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx`

### Légende sheet (non-data)

The workbook's first sheet, named exactly `Légende`, is pure documentation —
it explains which requested columns are not raw source data and must be
computed/derived before filling the sheet (e.g. médiane/P75/P90, délai
moyen). It is never a KPI: it is excluded entirely from
recognized/unknown/missing sheet counts (never downgraded to an
"unknown sheet" warning), and it is never listed under "Required sheet
names" below. KPI sheets start from the workbook's 2nd sheet onward, but
sheet **order** is otherwise irrelevant — every sheet is looked up by name,
never by position.

### Baseline vs incremental imports

Recommended behavior:
- first/base import: require all 18 KPI sheets;
- later incremental import: allow a subset of recognized KPI sheets if validation passes;
- unknown sheets: warning or rejection according to strict-mode configuration;
- never silently treat an unknown sheet as a KPI;
- the `Légende` sheet is neither "recognized" nor "unknown" — it is ignored outright.

## Required sheet names

- ACC-01
- INS-01
- INS-02
- INS-03
- FSC-01
- MAJ-01
- MAJ-02
- MAJ-03
- MAJ-04
- NOT-01
- NOT-02
- REC-01
- REC-02
- REC-03
- REC-04
- REC-05
- CQD-01
- CQD-02

## Generic workbook layout

Most sheets:
- row 1: KPI title
- row 2: synthetic/source note
- row 3: formula text
- row 4: blank
- row 5: headers
- row 6+: data

For Pandas, the main table usually starts with:
`header=4`.

Do not parse title/note/formula rows as data.

## Special sheets

### INS-02

Main table:
- columns A:I

National summary table:
- columns K:N

National summary headers:
- Mois
- Médiane nationale
- P75 national
- P90 national

### INS-03

Global table:
- columns A:F

Field analysis table:
- columns H:O

Both tables are required for the full KPI experience.

### MAJ-01

Main table:
- columns A:L

National summary table:
- columns N:Q

National summary headers:
- Mois
- Délai médian national
- P75 national
- P90 national

## Normalization

Normalize source headers to stable internal snake_case names.

Examples:
- `Province / Préfecture` → `province_prefecture`
- `Nombre total de ménages actifs` → `menages_actifs`
- `Nombre de ménages distincts soupçonnés` → `menages_soupconnes`

Source workbook remains immutable.

Trim text values.

Convert:
- dates → date/datetime
- month fields → consistent month/date representation
- numeric counts → integer where appropriate
- delays/percentiles → numeric
- categorical dimensions → normalized strings

Do not erase meaningful distinctions in source labels.

## Null semantics

Never globally use `fillna(0)`.

Examples:
- `0 dossiers finalisés` + null percentile is valid.
- `0 dossiers finalisés` + numeric percentile is invalid.
- missing metric is not equivalent to zero.

## Validation rules

### General
- count/volume fields >= 0
- denominators >= 0
- no invalid numeric text after coercion
- required dimensions cannot be silently replaced with empty strings
- duplicate natural keys inside one import are errors unless they can be deterministically aggregated without changing semantics

### ACC-01
`0 <= present_30j <= present_90j <= rnp_idcs_actif`

### INS-01
`0 <= finalise_30j <= finalise_60j <= finalise_90j <= initie`

### INS-02
for populated rows:
`median <= p75 <= p90`

### INS-03
`incoherents <= compared`

### MAJ-01
`finalized <= total_concerned`
for populated percentiles:
`median <= p75 <= p90`
if `finalized == 0`, percentile values must be null

### MAJ-04
`non_rescored_365 <= active_households`

### NOT-01
`heads_with_activity <= heads_with_phone`, where `heads_with_activity` is the
workbook's own precomputed union column ("chefs avec ≥1 activité observée
(OTP réussi ou notification reçue)") — the only valid numerator. Never
compute `heads_with_otp + heads_with_notification` as a substitute: a head
can trigger both events, so a naive sum double-counts the overlap between
the two populations. `heads_with_otp <= heads_with_activity` and
`heads_with_notification <= heads_with_activity` (a union can't be smaller
than either component). OTP réussi / notification reçue are secondary,
explanatory counts displayed alongside the combined rate, never summed into
it.

### NOT-02
`delivered + not_delivered == observable_sent`
`in_transit` is separate from observable mature deliveries per current workbook design.

### REC-03
`accepted <= final_decisions`

### REC-04
`clôturés` (`nb_reclamations_cloturees`) is a flow: safe to sum across any
set of rows/periods. `en cours` (`reclamations_en_cours`) is a
stock/snapshot: it must only ever be read for the most recent period in
whatever population is being aggregated (a single period for the headline
card, or — for a breakdown spanning a multi-month date range — the most
recent period within that range). Never sum `en cours` across periods; doing
so double-counts an open backlog that was already open in an earlier month.

### CQD-01
`confirmed_fraud <= closed_suspicions`
`suspicions_en_traitement` (in-progress suspicions) is an independent raw
count, distinct from `confirmed_fraud`/`closed_suspicions`.

### CQD-02
Rouge/orange are the only counts the source actually fills in; "Nombre
total de ménages soupçonnés" is blank on every row in practice. The KPI's
"total" ratio window is therefore **derived** as
`menages_soupconnes_rouge + menages_soupconnes_orange`, never read back from
that column. Enforced: `menages_soupconnes_rouge + menages_soupconnes_orange
<= menages_actifs`. If the source *does* populate its own total column, it
must agree with rouge + orange (`SumEquals`, skipped when blank). The
categories are mutually exclusive at the source (a household is counted
under exactly one of rouge/orange) — the app has no way to verify this from
aggregate counts alone, it is a source-side guarantee.

## Import atomicity

An import is all-or-nothing:
1. parse;
2. validate;
3. preview;
4. confirm;
5. commit transaction.

No partial persistence if validation fails.

## Deduplication / upsert

Imports must be idempotent.

For each KPI define a natural key from its grain/dimensions. A later accepted import is authoritative for identical natural keys.

Preview must report:
- rows new
- rows updated
- rows unchanged
- conflicts/errors

Recommended examples of natural-key dimensions:

- ACC-01: month + region + province + milieu + age_band
- INS-01: month + region + province + milieu + channel
- INS-02 main: month + region + province + milieu + channel
- INS-03 global: quarter + region + province + milieu
- INS-03 field: quarter + region + province + milieu + field + incoherence_type
- FSC-01: month + administrative_source + flow_type
- MAJ-01: month + update_type + complexity + region + province + milieu + channel
- MAJ-02: month_end + update_type + channel + region + province + milieu
- MAJ-03: month + update_type + channel + region + province + milieu
- MAJ-04: cutoff_date + region + province + milieu
- NOT-01: month + region + province + milieu + gender + age_band
- NOT-02: month + mail_type + region + province + milieu
- REC-01: deposit_month + recourse_motive + region + province + milieu
- REC-02: month + recourse_motive + region + province
- REC-03: decision_month + recourse_motive + region + province + milieu
- REC-04: deposit_month + channel + region + province + milieu
- REC-05: month + region + province + milieu
- CQD-01: period + suspicion_rule + suspected_fraud_type + region + province + milieu
- CQD-02: period + region + province + milieu

If implementation discovers an additional true grain column, include it rather than forcing collisions.

## Date/filter behavior

Filter on dates using the actual period semantics of the KPI:
- monthly sheets → month
- quarterly sheets → quarter
- cutoff/stock sheets → cutoff/month-end date

Do not pretend quarterly data are monthly.

## Baseline seed workbook

The synthetic seed workbook is suitable for:
- parser development;
- validation;
- dashboard testing;
- import/upsert testing.

It is not evidence of real RSU performance.
