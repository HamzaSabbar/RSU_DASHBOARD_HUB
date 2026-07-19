# Julia RSU dashboard datasets

Local copy imported from:

`/Users/omar/Downloads/julia-bundle-kit_v2.1/JuliaOfflineBundle/project/RSU202503`

The authoritative source directory is:

`/Users/omar/Downloads/julia-bundle-kit_v2.1/JuliaOfflineBundle/project/RSU202503/db/DATASET/dataps`

The project-local copy is the development source for all RSU dashboard data
products. Imported data files are intentionally ignored by Git.

## Raw CSV files

Located in `data/julia-rsu/raw/`:

| File | Platform use |
|---|---|
| `menage.csv` | Household geography, urban/rural area and household size. |
| `score.csv` | Score history and calculation dates. |
| `score_variable.csv` | Per-score variable contributions; large source for scoring quality, drivers and explainability. |
| `ref_variable.csv` | Score-variable reference. |
| `beneficiaire.csv` | Dated programme-beneficiary records; administrative-flow semantics still require confirmation. |
| `asd.csv` | Current ASD household membership. |
| `amot.csv` | Current AMO Tadamon household membership. |
| `amoa.csv` | Current AMOA household membership. |
| `ref_motif_beneficiaire.csv` | Beneficiary/exit-motif reference. |
| `parameters/rsu_parameters.json` | RSU calculation parameters. |

The complete local RAW layer is approximately 2.4 GB and contains about 67.7
million data rows. `score_variable.csv` accounts for approximately 63.4 million
of those rows and should be processed as an extended scoring tier rather than
scanned for every dashboard.

## Prepared Arrow files

Located in `data/julia-rsu/prepared/`. These are existing Julia analytical
examples, mainly useful as golden references for rescoring parity. They are not
the platform-wide source of truth. They use a `2024-03-01` cutoff and 30-day
score buckets.

| File | Dashboard use |
|---|---|
| `crossings_df.arrow` | Household-level ASD/AMOT threshold entries and exits. |
| `crossings_program_df.arrow` | Daily entry/exit aggregates by programme and urban/rural zone. |
| `delta_ise_df.arrow` | Household-level score changes used for volatility. |
| `menage_df.arrow` | Prepared household attributes and geographic identifiers. |
| `program_menage_df.arrow` | Household-to-programme mapping. |
| `region_df.arrow` | Region reference. |
| `province_df.arrow` | Province reference. |
| `score_at_cutoff_df.arrow` | Household score snapshot at the dataset cutoff. |
| `score_df.arrow` | Prepared score history after cutoff. |
| `beneficiaire_df.arrow` | Prepared beneficiary records. |
| `parameters.json` | Parameters used to generate the prepared dataset, including programme thresholds. |

## Generated platform releases

The running `analytics-worker` writes generated releases to
`data/analytics/releases/<release-key>/` in development. This directory is
Git-ignored and contains:

- `analytics.duckdb`: small read-only catalog whose views point at the release;
- `core/*.parquet`: shared typed core and derived tables;
- `products/programmes-sociaux-rescoring/*.parquet`: dashboard product tables;
- Arrow IPC copies of compact dashboard marts;
- `manifest.json`: source checksums, parameters, row counts, quality results and
  artifact inventory.

Do not edit a release in place. Queue another build and allow PostgreSQL to
atomically move the active release pointer only after validation succeeds.

## Programme mapping

- `asd` maps to dashboard code `ASD`.
- `amot` maps to dashboard code `AMO_TADAMON`.
- `amoa` maps to dashboard code `AMOA`.

## Important limitations

- The dataset is an example/analytical sample, not a complete national extract.
- Prepared crossings use 30-day buckets. Monthly and quarterly graphs can use
  them directly; weekly reporting should be recomputed from `raw/score.csv`.
- `crossings_program_df.arrow` does not contain region or province. Territorial
  reporting must use `crossings_df.arrow` joined to the household geography.
- Actual administrative admissions/removals must not be treated as identical
  to score-threshold crossings until the beneficiary-event rules are confirmed.
- RAW parameters currently use a different cutoff/bucket profile from the
  prepared example; transformation profiles must therefore be versioned.
- Some current dashboard metrics, including FMS, financial and communication
  measures, are not directly available in this CSV source and need an approved
  secondary source or removal.

## Related implementation documents

- [Platform-wide RSU data architecture plan](../../docs/rsu-data-platform-plan.md)
- [Programmes sociaux / Rescoring data-product addendum](../../docs/programmes-sociaux-rescoring-data-platform-plan.md)
- [Dashboard input template](../../docs/programmes-sociaux-rescoring-input-template.md)
