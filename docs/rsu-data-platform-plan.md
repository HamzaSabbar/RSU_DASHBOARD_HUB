# RSU Dashboard Hub — platform-wide data architecture plan

## Implementation status — 16 July 2026

The first platform-wide implementation is operational in this repository:

- Alembic revision `0006` adds PostgreSQL source batches, file manifests, core
  versions, product builds, artifacts, quality checks and immutable releases;
- the `analytics-worker` service validates the configured RAW directory and
  builds explicit-schema DuckDB/Parquet core tables;
- the large `score_variable.csv` file is processed as a separate
  `core-extended` artifact and is never scanned by ordinary dashboard calls;
- the Julia-compatible profile uses a `2024-03-01` cutoff, valid score range
  `5–15`, 30-day mean buckets and the source programme thresholds;
- the Programmes sociaux / Rescoring product publishes threshold crossings,
  daily flow, volatility, geography filters and Arrow IPC marts;
- the API opens only the active DuckDB catalog in read-only mode;
- dashboard responses use a release-versioned TTL/LRU cache, bounded by entry
  count and total bytes. A newly published release has a different cache key,
  so stale responses cannot leak across releases;
- the admin screen and `python -m data_platform.cli enqueue` can queue a full
  or light build; failed builds remain visible in PostgreSQL and never replace
  the active release.

The complete local sample build was verified against all 67,664,272 source
rows. The successful analytical release is about 215 MB with Zstandard-compressed
Parquet, compared with approximately 2.4 GB of RAW CSV.

The implemented delivery contract is a configured read-only RAW directory.
A production object-storage upload/session workflow, multi-node shared cache
(if the API is horizontally replicated), retention automation and additional
dashboard-specific marts remain deployment/product increments; they do not
block the current local single-node platform.

## 1. Scope correction

This is the master data-platform plan for **all RSU dashboards**, not only the
Programmes sociaux / Rescoring dashboard.

The primary source of truth is the CSV dataset located at:

`/Users/omar/Downloads/julia-bundle-kit_v2.1/JuliaOfflineBundle/project/RSU202503/db/DATASET/dataps`

For development, that source has been copied into `data/julia-rsu/raw/` and is
Git-ignored. The application must not query the Downloads directory directly.
Production will receive equivalent client extracts through a versioned upload
and object-storage process.

The platform must prepare this source once into reusable core facts and
dimensions, then build dashboard-specific analytical marts from the same
published dataset version.

```text
                         PostgreSQL control plane
                 users / jobs / versions / audit / release
                                  |
                                  v
Client CSV source -> immutable RAW -> DuckDB preparation -> curated core
                                                     |
                              +----------------------+---------------------+
                              |                      |                     |
                              v                      v                     v
                     Macro National mart    Social/Rescoring mart   Scoring marts
                              |                      |                     |
                              +----------------------+---------------------+
                                                     |
                                                     v
                                         FastAPI board endpoints
                                                     |
                                                     v
                                            All web dashboards
```

## 2. Source-of-truth inventory

The complete CSV source contains approximately **2.4 GB** and **67,664,272 data
rows**.

| Source file | Rows | Primary subject |
|---|---:|---|
| `menage.csv` | 499,999 | Household, geography and current household attributes |
| `score.csv` | 1,903,133 | Score events over time |
| `score_variable.csv` | 63,413,366 | Per-score variable contributions and corrected/calculated values |
| `ref_variable.csv` | 67 | Score-variable reference |
| `beneficiaire.csv` | 1,163,645 | Programme beneficiary records |
| `asd.csv` | 367,712 | Current ASD membership snapshot |
| `amot.csv` | 297,272 | Current AMO Tadamon membership snapshot |
| `amoa.csv` | 19,074 | Current AMOA membership snapshot |
| `ref_motif_beneficiaire.csv` | 4 | Beneficiary motif reference |
| `parameters/rsu_parameters.json` | — | Thresholds, score bounds and transformation parameters |

The `.rar` and `.xlsx` files in the same directory are delivery/archive copies,
not separate authoritative facts. The CSV files and approved parameter JSON are
the logical source contract.

## 3. What this source can and cannot support

### Directly supported

- household and geographic population analysis;
- current programme membership by ASD, AMOT and AMOA;
- score-event history and score distributions;
- latest-score snapshots;
- score changes, volatility and programme-threshold crossings;
- score-variable contributions, drivers and explainability;
- programme beneficiary records, subject to event-semantics validation;
- regional, provincial, commune and urban/rural analysis;
- selected-period analytics within the available score/beneficiary dates.

### Not automatically supported

The CSV directory does not currently provide an explicit authoritative source
for every metric shown in every existing or proposed dashboard:

- FMS treatment, blocked-case and fraud workflow facts;
- financial amounts, programme budgets and savings;
- communicated/non-communicated programme stocks;
- historical programme membership start/end dates;
- historical household size or historical geography;
- definitive administrative admissions/removals unless beneficiary semantics
  are confirmed;
- full national totals if this remains the approximately 10% analytical sample
  described by the Julia report.

Before migrating a dashboard, create a metric coverage matrix. Every KPI must be
classified as:

1. directly sourced from CSV;
2. deterministically derived from CSV;
3. supplied by another approved source;
4. unavailable and removed/labelled accordingly.

Do not invent unsupported metrics or use a score-threshold crossing as a silent
replacement for an administrative or financial event.

## 4. Architectural principle: one core, many data products

Do not build a separate ingestion pipeline for each dashboard. Build one
platform pipeline with four layers:

```text
RAW       Immutable client files and exact checksums
BRONZE    Typed source-shaped tables plus rejects and lineage
SILVER    Shared normalized RSU dimensions and facts
GOLD      Dashboard-specific marts and metric outputs
```

All dashboard marts must reference the same `core_dataset_version`. This gives
consistent households, geography, score rules, thresholds and dates across the
whole application.

Examples:

| Layer | Shared outputs |
|---|---|
| Bronze | Typed copies of menage, score, score_variable, beneficiary and programme lists |
| Silver | Household/geography dimensions, score events, score-variable facts, programme membership and beneficiary events |
| Derived Silver | Score snapshots, transitions, variable deltas, programme crossings and eligibility |
| Gold | Macro National, programmes/rescoring, volatility, scoring quality, territorial and future dashboard marts |

## 5. Technology responsibilities

### PostgreSQL: transactional control plane

PostgreSQL remains authoritative for:

- users, roles, authentication and login activity;
- board registration and access permissions;
- source registrations and upload sessions;
- ingestion/build jobs, stages, progress, errors and retries;
- dataset versions, source checksums and parameter versions;
- artifacts, quality results and lineage metadata;
- data-product builds and release manifests;
- active/superseded release pointers and rollback;
- audit logs and retention/deletion events.

PostgreSQL is designed for concurrent application transactions and MVCC:

- [PostgreSQL transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [PostgreSQL concurrency control](https://www.postgresql.org/docs/current/mvcc.html)

### DuckDB: preparation and analytics engine

DuckDB performs:

- explicit-schema CSV scans;
- structural and cross-file validation;
- deduplication, normalization and quarantine;
- joins across large household, score and score-variable facts;
- snapshots, transitions, variable deltas and threshold crossings;
- analytical mart builds;
- backend filter, aggregation and exploration queries.

DuckDB is embedded in the Python worker/API. It needs no Docker service or port.

### Parquet: canonical prepared storage

Persist Bronze/Silver/Gold tables as versioned Parquet. DuckDB can read these
files directly with filter and projection pushdown:

- [DuckDB Parquet support](https://duckdb.org/docs/stable/data/parquet/overview)

### Arrow: interoperability and optional exports

Use Arrow Tables/RecordBatches between DuckDB, PyArrow and notebooks. Export
`.arrow` IPC files where Julia compatibility or a downstream consumer requires
them, but do not make Arrow IPC the only recoverable prepared format:

- [DuckDB Arrow integration](https://duckdb.org/docs/stable/clients/python/overview)
- [Exporting DuckDB results to Arrow](https://duckdb.org/docs/current/guides/python/export_arrow)

### Object storage/local analytics volume: large files

Store immutable RAW, Parquet, optional Arrow, validation reports and optional
DuckDB snapshots outside PostgreSQL.

## 6. Platform-wide target architecture

```text
Browser/Admin
  |
  +--> create upload session ------------------------------+
  |                                                        |
  +--> stream/direct-upload client bundle                  v
                                                   PostgreSQL
                                             dataset batch + job
                                                          |
                                                          v
                                                Analytics worker
                                               single write process
                                                          |
                   +--------------------------------------+--------------------------------+
                   |                                      |                                |
                   v                                      v                                v
          Explicit-schema scan                     Quality/rejects                  Transform SQL
                   |                                                                       |
                   +--------------------------------------+--------------------------------+
                                                          v
                                                  Versioned Parquet
                                              core + derived + marts
                                                          |
                                     +--------------------+--------------------+
                                     |                                         |
                                     v                                         v
                           Optional Arrow exports                    Immutable DuckDB snapshot
                                     |                                         |
                                     +--------------------+--------------------+
                                                          v
                                              PostgreSQL release activation
                                                          |
                                                          v
                                               FastAPI read-only queries
                                                          |
                                                          v
                                               Board-specific dashboard JSON
```

Only the analytics worker writes a dataset generation. API processes read only
completed immutable generations. This matches DuckDB's normal multi-process
concurrency model:

- [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency)

## 7. Platform storage layout

```text
rsu-dashboard/
  sources/rsu/
    {source_batch_id}/
      raw/
        original.zip
        manifest.json
        files/
          menage.csv
          score.csv
          score_variable.csv
          beneficiaire.csv
          asd.csv
          amot.csv
          amoa.csv
          ref_variable.csv
          ref_motif_beneficiaire.csv
          parameters/rsu_parameters.json

  datasets/rsu/
    {core_dataset_version}/
      bronze/
        *.parquet
        rejects/*.parquet
      silver/
        dimensions/*.parquet
        facts/*.parquet
        derived/*.parquet
      gold/
        macro-national/*.parquet
        programmes-sociaux-rescoring/*.parquet
        scoring-volatility/*.parquet
        scoring-quality/*.parquet
        territorial/*.parquet
      exports/arrow/*.arrow
      catalog/analytics.duckdb
      manifest.json
      validation.json
      lineage.json
      release.json
      _SUCCESS
```

A generation is immutable after `_SUCCESS` is written. New source or new
transformation logic creates a new version; activation changes only a PostgreSQL
pointer.

## 8. Client/source contract

The production source bundle should include:

```text
rsu-source-v1.zip
  manifest.json
  menage.csv
  score.csv
  score_variable.csv
  beneficiaire.csv
  asd.csv
  amot.csv
  amoa.csv
  ref_variable.csv
  ref_motif_beneficiaire.csv
  parameters/rsu_parameters.json
```

Because the variable fact is approximately 2.1 GB, production should ultimately
use resumable/direct-to-object-storage upload. A full-memory Next.js/FastAPI
proxy is not acceptable.

The manifest should identify:

- schema and source-system versions;
- extract ID and extraction timestamp;
- data coverage start/end;
- membership snapshot date;
- each logical filename, byte size and SHA-256;
- parameter version;
- whether the extract is a full snapshot or delta.

Every loaded row should carry technical lineage:

```text
source_batch_id
source_file
source_row
ingested_at
row_hash
```

## 9. Shared Bronze and Silver model

### Bronze tables

- `bronze_household`;
- `bronze_score_event`;
- `bronze_score_variable`;
- `bronze_beneficiary`;
- `bronze_program_membership`;
- `bronze_variable_reference`;
- `bronze_motif_reference`;
- `bronze_parameters`;
- `bronze_rejected_rows`.

Bronze remains close to the source, preserving raw values alongside parsed
values and validation flags.

### Shared dimensions

- `dim_household`;
- `dim_region`;
- `dim_province`;
- `dim_commune`;
- `dim_program`;
- `dim_score_variable`;
- `dim_beneficiary_motif`;
- `dim_program_threshold`;
- `dim_volatility_band`;
- `dim_date`.

Preserve approved French display labels. Normalized labels are matching keys,
not replacements for UI values.

### Shared base facts

- `fact_score_event`: cleaned authoritative score events;
- `fact_score_variable_contribution`: contribution/value by score and variable;
- `fact_beneficiary_event`: prepared beneficiary records;
- `fact_program_membership_snapshot`: household/programme membership as of an
  explicit snapshot date.

### Shared derived facts

- `fact_latest_score_snapshot`;
- `fact_score_transition`;
- `fact_score_variable_delta`;
- `fact_program_threshold_crossing`;
- `fact_program_eligibility_snapshot`;
- `fact_score_reconstruction_quality`.

These facts are reusable across dashboards. A dashboard must not recalculate
them independently with different hidden rules.

## 10. Data-product mart strategy

Each board becomes a versioned data product over the shared core.

### Macro National

Possible CSV-derived marts:

- household/score coverage snapshots;
- registrations or first-score events, if the approved definition maps to
  `type_demande`;
- current programme membership counts;
- geographic score/population summaries.

Existing FMS, fraud, financial and communication KPIs require another source or
must remain on the existing Excel pipeline until coverage is resolved.

### Programmes sociaux / Rescoring

- programme eligibility snapshots;
- rescoring threshold entries/exits;
- volatility bands;
- regional/provincial programme flow;
- current-member versus all-evaluated population scopes.

Detailed rules remain in
`docs/programmes-sociaux-rescoring-data-platform-plan.md`.

### Scoring volatility and quality

- score-distribution and drift marts;
- transition intensity/frequency;
- variable contribution and variable-delta marts;
- reconstruction residuals and data-quality anomalies;
- urban/rural and territorial comparisons.

### Future dashboards

New boards should declare required marts and metrics rather than creating their
own RAW parser.

Extend `BoardSpec` conceptually with:

```text
required_data_products
minimum_core_schema_version
query_service
metric_catalog_namespace
```

A board is available only when its required product build is `ready` for the
active core dataset version.
A board is available only when its required product build is `ready` for the
active core dataset version.

## 11. End-to-end platform pipeline

### Stage 1 — Land the source

1. Register the source batch in PostgreSQL.
2. Stream or direct-upload the archive/files.
3. Calculate server-side SHA-256 and size.
4. Preserve exact bytes in immutable RAW storage.
5. Safely validate/extract approved files.
6. Deduplicate by complete content fingerprint.

### Stage 2 — Structural validation

1. Validate manifest, required files and approved filename mapping.
2. Validate exact headers, encoding and delimiter.
3. Scan with explicit DuckDB types and formats.
4. Store malformed rows in a rejects dataset.
5. Compare parsed, rejected and source line counts.
6. Stop before transformation on blocking failures.

DuckDB supports explicit CSV schemas and reject capture:

- [DuckDB CSV import](https://duckdb.org/docs/stable/data/csv/overview)
- [DuckDB faulty CSV handling](https://duckdb.org/docs/current/data/csv/reading_faulty_csv_files)

### Stage 3 — Build Bronze

- add lineage columns;
- normalize empty/missing representations without losing raw values;
- create typed Parquet source tables;
- separate valid, warning and quarantined records;
- record row counts, schemas and date ranges.

### Stage 4 — Build shared Silver

- deduplicate with explicit business-key rules;
- create geography/programme/reference dimensions;
- calculate `score_final = COALESCE(score_corrige, score_calcule)`;
- normalize programme and request-type codes;
- construct membership snapshots and beneficiary facts;
- join score variables to score and variable reference;
- build shared snapshots, transitions, crossings and reconstruction facts.

### Stage 5 — Build Gold data products

Build each mart from the same core version. A failure in one data product must
not corrupt another product or the shared core.

### Stage 6 — Reconcile and publish

- detail-to-aggregate reconciliation;
- geographic roll-up reconciliation;
- temporal coverage checks;
- threshold and parameter traceability;
- product-specific metric tests;
- manifest/lineage generation;
- `_SUCCESS` marker;
- PostgreSQL transactional release activation.

### Stage 7 — Serve

- API reads the active platform release from PostgreSQL;
- each board opens only its ready immutable mart/core artifacts;
- DuckDB executes parameterized read-only queries;
- browser receives small aggregated JSON.

## 12. Parameter and methodology governance

The current source demonstrates why parameters cannot be treated casually:

| Configuration | Cutoff | Bucket | Time-series step |
|---|---:|---:|---|
| RAW `rsu_parameters.json` | 2022-11-23 | 90 days | monthly |
| Existing prepared example | 2024-03-01 | 30 days | daily |

The RAW parameters therefore do not reproduce the existing prepared example by
themselves.

Create a versioned `transformation_profile` containing:

- score floor/cap;
- cutoff and bucket anchor;
- bucket width and aggregation function;
- threshold set/effective dates;
- request-type mapping version;
- volatility-band version;
- population scope;
- code/SQL pipeline version.

Every artifact and metric response must expose the profile/version used.

Recommended rollout:

1. reproduce the Julia prepared generation with a frozen compatibility profile;
2. establish golden parity tests;
3. approve platform production methodology;
4. introduce later methodology changes as new core versions, never silent
   mutations.

## 13. Special handling for `score_variable.csv`

This table dominates the source: approximately 2.1 GB and 63.4 million rows.
It should not be scanned for dashboards that only need households, scores or
programme crossings.

Create two build tiers:

```text
Core-light build
  household + score + beneficiary + programme membership
  supports most population/programme dashboards

Core-extended scoring build
  adds score_variable + ref_variable
  supports drivers, explainability, reconstruction and advanced volatility
```

Recommendations:

- convert the source once into compressed Parquet;
- cluster/order output by score ID and variable ID where useful;
- keep a score-to-household/date lookup;
- build pre-aggregated variable marts for interactive dashboards;
- do not return raw variable rows to the browser;
- configure worker memory/spill limits and monitor temporary disk;
- avoid excessive province/date partitions and small files.

At the present size, partition only when it materially reduces scans. DuckDB
recommends avoiding many small partitions:

- [DuckDB partitioned writes](https://duckdb.org/docs/lts/data/partitioning/partitioned_writes)

## 14. PostgreSQL platform metadata model

### `data_sources`

- source name/type and owner;
- expected contract/schema version;
- delivery method and storage prefix;
- active/retention settings.

### `source_batches`

- extract ID, source and schema version;
- source period/extraction timestamp;
- status/stage/progress;
- raw manifest path and content hash;
- creator and lifecycle timestamps;
- failure summary.

### `source_files`

- batch and logical file name;
- path, byte size and SHA-256;
- row/reject count and schema fingerprint;
- minimum/maximum dates and validation status.

### `core_dataset_versions`

- source batch;
- transformation profile and pipeline version;
- deterministic version fingerprint;
- Bronze/Silver prefixes;
- status and validation summary.

### `data_product_builds`

- core dataset version;
- product/board slug and product version;
- Gold artifact prefix;
- status, metrics and quality summary;
- build timestamps and error.

### `dataset_artifacts`

- dataset/product owner;
- logical table, layer and format;
- path, schema JSON, row count and checksum;
- date range and creation metadata.

### `dataset_quality_checks`

- stable rule code/version;
- layer/table/product;
- severity, pass/fail and affected count;
- safe observed/expected metadata.

### `platform_releases`

A release binds one core version to approved data-product builds:

```text
release_id
core_dataset_version
macro_national_product_version
programmes_rescoring_product_version
scoring_quality_product_version
...
is_active
published_by / published_at
superseded_release_id
```

Release activation is one PostgreSQL transaction. Rollback changes the active
release pointer; it does not rewrite analytical files.

## 15. DuckDB runtime model

Do not share one mutable `.duckdb` file among API/worker processes.

- analytics workers are the only writers;
- every core/product generation uses an isolated staging directory;
- workers close files before `_SUCCESS` and publication;
- API connections are read-only and per thread/request execution context;
- FastAPI runs synchronous DuckDB queries in a bounded thread pool;
- queries use parameterized filter values and allowlisted dimensions;
- configure memory, threads, spill directory and maximum spill size.

Local Docker:

```text
analytics-worker -> analytics volume read/write
api              -> analytics volume read-only
```

Multi-host production:

- immutable Parquet/Arrow in object storage;
- local read-through cache per API instance or a dedicated analytics service;
- no mutable DuckDB file on NFS/shared network storage.

## 16. Platform and board APIs

### Platform administration

```text
POST /api/data/sources/rsu/batches/init
POST /api/data/sources/rsu/batches/{id}/complete
GET  /api/data/batches/{id}/status
GET  /api/data/batches/{id}/validation
GET  /api/data/releases/active
POST /api/data/releases/{id}/activate
POST /api/data/releases/{id}/rollback
```

### Shared metadata

```text
GET /api/data/catalog
GET /api/data/coverage
GET /api/data/lineage/{metricCode}
```

### Board endpoints

Each board keeps its own typed response contract:

```text
GET /api/boards/{boardSlug}/filters
GET /api/boards/{boardSlug}/dashboard
```

Common filters:

- start/end date;
- region and dependent province;
- programme when applicable;
- display grain;
- approved population/methodology scope when applicable.

Every response should contain:

- platform release ID;
- core and product versions;
- data coverage/reference date;
- transformation/methodology version;
- applied filters;
- data-quality warning summary.

## 17. Metric catalog and lineage

Create a shared metric catalog before migrating dashboards.

Each metric requires:

```text
metric_code
French/English label
business definition
unit
population scope
time grain
source tables/fields
transformation profile
aggregation rule
supported filters
owner/approver
quality/reconciliation rules
```

Examples of distinctions that must remain explicit:

- current programme membership versus beneficiary event;
- rescoring threshold crossing versus administrative entry/exit;
- household count versus summed current household size;
- all evaluated RSU households versus current programme members;
- snapshot value versus period flow;
- sample count versus national count.

## 18. Platform data quality

### Source-level blocking checks

- required files/headers missing;
- invalid parameter/manifest JSON;
- unsupported schema version;
- primary identifiers nonnumeric/missing;
- conflicting duplicates;
- invalid dates/booleans;
- contradictory geography relationships;
- source count/reject mismatch.

### Shared fact checks

- scores reference households and score variables reference scores/variables;
- score-final rule is deterministic;
- score bounds and quarantine reconcile;
- programme lists reference households;
- thresholds are complete and unique;
- snapshots have one record per approved key;
- transition/crossing rules hold exactly.

### Product checks

- Gold totals equal Silver detail;
- province + unknown reconcile to region/national totals;
- snapshot values are never summed across dates;
- overlapping programme membership is handled explicitly;
- unsupported metrics cannot publish as fabricated zeroes.

The current sample already contains duplicate identifiers, out-of-bound scores,
unmatched references and substantial ASD/AMOT membership overlap. Quality rules
must distinguish exact duplicates, conflicting duplicates, quarantine and
business-valid overlap.

## 19. Idempotency, lineage and reproducibility

Core version fingerprint:

```text
ordered source file SHA-256 values
+ source schema version
+ approved parameter/transformation profile
+ pipeline code/SQL version
```

Product version fingerprint:

```text
core dataset version
+ product SQL/code version
+ metric catalog version
```

Required behavior:

- identical source/profile/code reuses an existing successful generation;
- new code/profile produces a new version even with identical CSVs;
- failed builds never activate;
- source -> core -> product -> dashboard lineage is queryable;
- old releases remain available for controlled rollback;
- raw bytes are retained according to policy.

## 20. Full rebuild first, incremental later

Version one should perform immutable full builds. The source behaves primarily
as a complete snapshot, and stable delta semantics are not documented.

Future incremental processing requires:

- stable source event/update IDs;
- membership snapshot dates and removal semantics;
- dated household/geography changes;
- late score-event handling;
- explicit threshold/parameter effective dates;
- affected-household recomputation rules.

Any threshold, score bound, bucket method, variable formula or geography-history
change may require a full rebuild.

## 21. Security and operations

- encrypt source and prepared data in transit/at rest;
- least-privilege PostgreSQL/object-storage identities;
- viewer/editor/admin separation;
- no raw rows or household IDs in logs;
- read-only API analytics access;
- safe archive extraction and strict path allowlists;
- no arbitrary SQL endpoints;
- no unapproved DuckDB extensions;
- resource limits for the 63.4M-row variable fact;
- separate backups for PostgreSQL control state and immutable data objects;
- tested restore, rollback, retention and deletion procedures.

DuckDB runs with backend filesystem privileges, so file and SQL input must be
strictly controlled:

- [Securing DuckDB](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview)

## 22. Repository organization

```text
apps/api/data_platform/
  contracts/
  ingestion/
  validation/
  storage/
  metadata/
  duckdb/
  sql/bronze/
  sql/silver/
  sql/products/{product_slug}/
  publication/
  worker.py

apps/api/boards/{board_slug}/
  router.py
  schemas.py
  service.py
  queries.py
  spec.py
```

Board code should query published products. It should not parse CSV, rebuild
shared score facts or own a separate data-version lifecycle.

## 23. Migration plan

### Phase 0 — Source and metric coverage

- approve the CSV/parameter contract;
- create complete dashboard-to-source coverage matrix;
- identify unsupported FMS/financial/communication metrics;
- approve population, temporal and threshold semantics;
- define metric catalog v1.

Exit: every current dashboard element has an approved source/derivation or an
explicit removal/secondary-source decision.

### Phase 1 — Platform control plane and landing

- add DuckDB/PyArrow dependencies and analytics configuration;
- add PostgreSQL source/core/product/release metadata;
- add streaming/resumable landing and checksums;
- create platform worker and analytics volume;
- implement strict contracts/rejects.

Exit: full source snapshot lands safely without full-memory buffering.

### Phase 2 — Shared Bronze/Silver core-light

- household/geography;
- scores;
- programme membership;
- beneficiary records;
- parameter governance;
- Parquet generation and quality reports.

Exit: reusable core-light release passes reconciliation.

### Phase 3 — Extended scoring core

- score-variable ingestion;
- variable reference;
- contribution/delta/reconstruction facts;
- performance tuning and pre-aggregations.

Exit: 63.4M-row source processes within approved resource/runtime limits.

### Phase 4 — First data products

Recommended order:

1. Programmes sociaux / Rescoring, because the RAW mapping is already studied;
2. scoring volatility/quality;
3. CSV-supported Macro National metrics;
4. territorial and future products.

Exit: each product has typed API, lineage and Gold reconciliation.

### Phase 5 — Dashboard cutover

- connect board filters/charts to product APIs;
- run old/new comparison where an old source exists;
- keep existing Excel Macro pipeline until coverage gaps are resolved;
- remove hardcoded values;
- expose release/data/methodology metadata.

Exit: each migrated dashboard is signed off independently.

### Phase 6 — Production hardening

- direct/resumable object storage upload;
- monitoring, capacity and query limits;
- backup/restore and rollback drill;
- retention/deletion and security review;
- full-source nightly acceptance and performance suite.

## 24. Immediate decisions

| Decision | Recommendation |
|---|---|
| Authoritative source | CSV + approved parameter JSON, immutable per source batch |
| Canonical prepared format | Parquet |
| Arrow | Internal interchange + optional compatibility exports |
| Analytics engine | Embedded DuckDB |
| App/control database | PostgreSQL |
| First processing mode | Full immutable build |
| Score-variable build | Separate extended tier, not required by every dashboard |
| Dashboard architecture | Shared core + versioned board-specific Gold marts |
| Existing Excel pipeline | Keep temporarily for metrics not derivable from CSV |
| Activation | PostgreSQL platform release transaction |

## 25. Definition of success

The platform is successful when:

1. one client CSV source batch is preserved and versioned once;
2. every prepared fact and dashboard metric traces back to source files/rows,
   parameters and code version;
3. shared household/score/geography logic is identical across dashboards;
4. the 63.4M-row score-variable table is processed without burdening dashboards
   that do not require it;
5. PostgreSQL activates/rolls back a coherent multi-dashboard release;
6. DuckDB reads only immutable prepared data in application query paths;
7. unsupported metrics are explicit rather than silently fabricated;
8. all dashboards expose data coverage and methodology metadata;
9. full-source rebuild, quality, security and recovery procedures are tested;
10. adding a new dashboard means adding a Gold data product and typed API—not a
    new RAW ingestion pipeline.
