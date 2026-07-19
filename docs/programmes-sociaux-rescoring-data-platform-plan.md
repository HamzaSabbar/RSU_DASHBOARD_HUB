# Programmes sociaux / Rescoring — data-product implementation addendum

> This document now describes the Programmes sociaux / Rescoring data product.
> The shared ingestion, PostgreSQL/DuckDB platform, source-of-truth and
> multi-dashboard release architecture are defined in
> [RSU platform-wide data architecture plan](rsu-data-platform-plan.md).
> Dashboard-specific code must reuse that platform rather than create a separate
> RAW pipeline.

## 1. Executive decision

The proposed PostgreSQL + DuckDB split is appropriate for this project.

- PostgreSQL remains the transactional control plane: application users,
  permissions, upload sessions, processing jobs, dataset versions, validation
  results, activation, rollback and audit history.
- DuckDB becomes the analytical engine: CSV validation, typing, joins, score
  preparation, score transitions, programme-threshold crossings, snapshots and
  dashboard aggregations.
- Object storage or the local analytics volume holds the large files. Millions
  of household and score rows should not be copied into PostgreSQL.
- The client RAW bundle remains immutable. Every prepared dataset is a new,
  versioned and reproducible generation.

The recommended durable prepared format is Parquet, with optional Arrow IPC
exports for Julia compatibility and Arrow Tables/RecordBatches for efficient
Python interchange. DuckDB remains the engine in both cases.

```text
Client RAW CSV bundle
        |
        v
Object storage: immutable RAW version
        |
        v
Single analytics worker + DuckDB
  validate -> normalize -> transform -> reconcile
        |
        +--> canonical prepared Parquet
        +--> optional Arrow IPC exports
        +--> optional immutable analytics.duckdb snapshot
        +--> manifest + validation report
        |
        v
PostgreSQL transaction activates the completed dataset version
        |
        v
FastAPI reads active version -> DuckDB read-only analytics -> small JSON
        |
        v
Programme / region / province / selected-period dashboard
```

## 2. Why Parquet should accompany Arrow

Arrow and Parquet solve different problems:

| Format | Best use in this project | Important characteristic |
|---|---|---|
| RAW CSV | Client delivery and immutable audit source | Human-readable but slow, large and not self-describing |
| Arrow Table / RecordBatch | In-memory transfer between DuckDB, PyArrow, Python and notebooks | Fast columnar interchange without converting every row to Python objects |
| Arrow IPC `.arrow` | Optional Julia-compatible prepared export | Useful compatibility artifact, but not the only durable analytical copy |
| Parquet | Canonical prepared storage | Compressed, columnar, supports projection and filter pushdown |
| `.duckdb` | Optional immutable query snapshot/catalog | Useful for repeated joins and pre-aggregated dashboard queries |

DuckDB documents direct Arrow integration and Arrow result streaming, but its
core Parquet integration is particularly suitable for persistent analytical
files and supports filter/projection pushdown:

- [DuckDB Python and Arrow integration](https://duckdb.org/docs/stable/clients/python/overview)
- [Exporting DuckDB results to Arrow](https://duckdb.org/docs/current/guides/python/export_arrow)
- [DuckDB Parquet support](https://duckdb.org/docs/stable/data/parquet/overview)

Recommendation:

```text
DuckDB relation
  -> Parquet: canonical prepared file used by production analytics
  -> Arrow IPC: compatibility/export artifact when required
  -> Arrow RecordBatch: in-process streaming between Python components
```

The existing Julia Arrow files should be treated as golden reference outputs
for parity testing, not as the only production storage format.

## 3. Current repository baseline

The project already has much of the control plane:

- PostgreSQL 16, SQLAlchemy and Alembic migrations are configured.
- Users, roles, boards, report jobs, active/superseded batches and audit logs
  already live in PostgreSQL.
- A separate worker already claims queued jobs safely from PostgreSQL.
- Local and GCS object-storage adapters already exist.
- The Docker ports are already non-default externally: web 3100, API 8100 and
  PostgreSQL 5433. DuckDB is embedded and needs no service or network port.

The reusable reference points are:

- `apps/api/reports/service.py`: asynchronous job lifecycle.
- `apps/api/reports/repository.py`: PostgreSQL queue claiming.
- `apps/api/reports/storage.py`: local/GCS artifact storage.
- `apps/api/db/models.py`: users, uploads, batches and fact models.
- `docker-compose.yml`: PostgreSQL, API, worker and web services.

The current gaps are:

- `duckdb` and `pyarrow` are not dependencies.
- The Programmes sociaux router exposes no data endpoints.
- The page still uses hardcoded arrays.
- The current upload path accepts only one XLSX file, is limited to 50 MB and
  reads the complete upload into memory.
- The compatible RAW CSV set is about 272 MB and 4.23 million rows.
- `data/julia-rsu` is a local reference fixture and is not mounted into the
  containers.
- Existing PostgreSQL `report_program_*` tables serve Macro National and do not
  contain household score transitions or threshold-crossing details.

The first implementation should therefore add the new pipeline without
rewriting or migrating the working Macro National pipeline.

## 4. System responsibility boundary

### PostgreSQL owns

- application users, passwords, roles and login timestamps;
- board definitions and permissions;
- upload sessions and processing jobs;
- dataset batch/version status and progress stage;
- file paths, sizes, SHA-256 checksums and row counts;
- schema version and transformation/pipeline version;
- thresholds and other business parameters used for a generation;
- validation and reconciliation summaries;
- active/superseded dataset pointers;
- audit events, retries, activation and rollback.

### DuckDB owns

- explicit-schema CSV scanning;
- malformed-row detection and data-quality queries;
- deduplication and type normalization;
- score-final calculation;
- household/programme/geography joins;
- score snapshots and score transitions;
- ASD/AMOT threshold crossings;
- eligibility, flow, volatility and territorial aggregations;
- notebook and backend analytical queries.

### Object storage or analytics volume owns

- the immutable original archive and extracted RAW files;
- prepared Parquet and optional Arrow files;
- optional immutable `.duckdb` snapshot;
- manifest and validation JSON artifacts;
- temporary worker spill files until a job finishes.

### The browser owns only

- upload initiation and progress display;
- validated filters;
- rendering small aggregated JSON responses.

The browser must never receive household-level Arrow or RAW data and must never
submit arbitrary SQL.

## 5. Client RAW bundle contract

For the first release, ask the client for one ZIP file. It is simpler to upload,
version and audit than a browser folder upload.

```text
rsu-rescoring-raw-v1.zip
  manifest.json                         recommended
  menage.csv                            required
  score.csv                             required
  beneficiaire.csv                      required for beneficiary analysis
  asd.csv                               required
  amot.csv                              required
  ref_motif_beneficiaire.csv            optional but recommended
  parameters/rsu_parameters.json        required
```

### Expected RAW schemas

| File | Grain/key | Required columns |
|---|---|---|
| `menage.csv` | One row per household | `menage_ano`, `milieu`, region/province/commune IDs and labels, `taille_menage` |
| `score.csv` | One score event | `menage_ano`, `score_id_ano`, `type_demande`, `score_corrige`, `score_calcule`, `date_calcul` |
| `beneficiaire.csv` | Beneficiary record/event | `menage_ano`, `partner_id`, `motif`, `date_insert`, `actif` |
| `asd.csv` | Current membership list | `menage_ano` |
| `amot.csv` | Current membership list | `menage_ano` |
| `ref_motif_beneficiaire.csv` | Motif reference | motif code and label |
| `rsu_parameters.json` | Transformation/business parameters | score bounds, bucket settings, cutoff and programme thresholds |

### Recommended manifest fields

```json
{
  "schema_version": "rsu-raw-v1",
  "extract_id": "CLIENT-2026-03-04-001",
  "source_system": "RSU",
  "extracted_at": "2026-03-04T12:00:00Z",
  "coverage_start": "2022-11-23",
  "coverage_end": "2026-03-04",
  "files": [
    {"logical_name": "score", "path": "score.csv", "sha256": "..."}
  ]
}
```

The server must calculate its own checksum and must not trust a client checksum
without comparison.

### ZIP protections

Before extraction, reject:

- absolute paths, `..` traversal and symbolic links;
- duplicate logical filenames;
- unapproved extensions or unexpected executables;
- excessive entry count, compressed size, expanded size or compression ratio;
- missing required files;
- files whose actual checksum differs from the manifest.

## 6. Versioned storage layout

Use immutable dataset IDs and never overwrite an active generation:

```text
rsu-dashboard/
  datasets/programmes-sociaux-rescoring/{dataset_id}/
    raw/
      original.zip
      manifest.json
      extracted/
        menage.csv
        score.csv
        beneficiaire.csv
        asd.csv
        amot.csv
        ref_motif_beneficiaire.csv
        parameters/rsu_parameters.json
    staging/{job_id}/
      temporary.duckdb
      spill/
    prepared/{pipeline_version}/
      parquet/
        dim_household.parquet
        fact_score_event.parquet
        bridge_household_program.parquet
        fact_beneficiary_event.parquet
        fact_score_transition.parquet
        fact_program_crossing.parquet
        snapshot_program_eligibility.parquet
        agg_program_flow_geo_day.parquet
        agg_score_volatility_geo_day.parquet
      arrow/
        fact_score_transition.arrow
        fact_program_crossing.arrow
        ... optional compatibility exports
      analytics.duckdb                 optional immutable snapshot
      manifest.json
      validation.json
      _SUCCESS
```

At the present data size, prefer one reasonably sized Parquet file per logical
table. Avoid partitioning by province and date because that would create many
small files. Introduce year/programme partitioning only when tables grow enough
to keep partitions substantial. DuckDB warns that excessive small partitions
are expensive:

- [DuckDB partitioned writes](https://duckdb.org/docs/lts/data/partitioning/partitioned_writes)

## 7. End-to-end processing workflow

### Stage 1 — Create upload session

1. Admin/editor starts an import for the Programmes sociaux board.
2. FastAPI creates a PostgreSQL dataset batch with status `uploading`.
3. PostgreSQL returns `dataset_id`, `job_id` and the upload destination.

### Stage 2 — Stream and preserve RAW

1. Stream the archive to storage; do not call `await upload.read()`.
2. Calculate SHA-256 and byte count while streaming.
3. Record the raw object path and checksum in PostgreSQL.
4. Safely extract the allowlisted files into the versioned RAW prefix.
5. Generate a server-side manifest if the client did not provide one.

For local development, a streaming FastAPI endpoint is acceptable. For
production object storage, prefer a presigned/resumable direct browser upload
so the 272+ MB payload is not buffered by both Next.js and FastAPI.

### Stage 3 — Structural validation

1. Verify required files, names, headers and encoding.
2. Read CSVs with explicit types and date formats.
3. Capture malformed lines into a rejects dataset.
4. Compare parsed and rejected row counts.
5. Stop before transformation when blocking checks fail.

DuckDB supports explicit CSV column types and rejects tables:

- [DuckDB CSV import](https://duckdb.org/docs/stable/data/csv/overview)
- [DuckDB faulty CSV handling](https://duckdb.org/docs/current/data/csv/reading_faulty_csv_files)

### Stage 4 — Normalize and transform

1. Normalize programme codes (`asd` -> `ASD`, `amot` -> `AMO_TADAMON`).
2. Parse timestamps and booleans with controlled rules.
3. Calculate `score_final = COALESCE(score_corrige, score_calcule)`.
4. Preserve invalid/out-of-range rows in quarantine instead of silently losing
   them.
5. Deduplicate on documented business keys.
6. Join geography and programme membership.
7. Build score snapshots, transitions and threshold crossings.
8. Build daily geographic aggregates used by the API.

### Stage 5 — Reconcile

Run blocking reconciliation queries before publication:

- every aggregate total equals its detailed source total;
- `entries + exits` equals all classified crossings;
- no crossing exists without a household, programme, threshold and date;
- regional totals equal their provincial children plus explicitly reported
  unknown geography;
- eligibility snapshots contain one row per date/programme/province;
- output row counts and date ranges are plausible and non-empty.

### Stage 6 — Publish

1. Write Parquet and optional Arrow artifacts under the new version.
2. Write the immutable manifest and validation report.
3. Close the writer connection.
4. Create `_SUCCESS` only after every artifact is complete.
5. Register artifact metadata in PostgreSQL.
6. In one PostgreSQL transaction, deactivate the previous version and activate
   the new version.
7. Keep the previous version for rollback and audit.

### Stage 7 — Query

1. API reads the active dataset ID from PostgreSQL.
2. It validates and allowlists filters.
3. It opens only immutable prepared files/read-only DuckDB.
4. DuckDB returns aggregated results.
5. FastAPI returns small JSON, including dataset and methodology metadata.

## 8. Prepared analytical model

The prepared layer should separate reusable detail facts from dashboard
aggregates.

### `dim_household`

One row per `menage_ano`:

- household identifier;
- `milieu`;
- region, province and commune IDs and labels;
- current household size and household attributes;
- source dataset ID.

Uniqueness: `menage_ano`.

### `fact_score_event`

One cleaned score calculation:

- `score_id_ano`, `menage_ano`, request type;
- calculated, corrected and final score;
- calculation timestamp/date;
- valid-score flag and rejection reason;
- source dataset ID.

Uniqueness: `score_id_ano`, with a documented fallback if the source violates
that key.

### `bridge_household_program`

One household/programme association:

- `menage_ano`;
- `program_code`;
- source (`asd.csv`, `amot.csv` or another future source);
- population scope (`CURRENT_MEMBERSHIP_LIST`);
- dataset/reference date.

Uniqueness: `menage_ano + program_code + dataset_id`.

### `fact_beneficiary_event`

Prepared `beneficiaire.csv` rows:

- household and programme;
- motif code and resolved label;
- insertion timestamp;
- active value;
- derived event direction only after the business semantics are approved.

Do not call this an administrative entry/exit fact until the meaning of
`actif`, repeated records and motifs is formally confirmed.

### `fact_score_transition`

One transition between two comparable household scores:

- household, geography and transition date;
- previous/current score and score IDs;
- `delta_ise`, `abs_delta_ise`, elapsed days;
- transition methodology and bucket size;
- score/parameter version.

Recommended key: deterministic hash of dataset, methodology, household and the
two endpoint score IDs/dates.

### `fact_program_crossing`

One programme-threshold crossing:

- transition key and household;
- programme and threshold;
- previous/current score;
- `IN` or `OUT`;
- crossing date;
- geography;
- population scope and methodology version.

### `snapshot_program_eligibility`

One snapshot date/programme/province:

- households with a valid score;
- eligible households after threshold;
- non-eligible households;
- threshold and threshold version;
- explicit population scope.

Snapshots must never be summed across dates. The API chooses the latest snapshot
on or before the selected end date.

### `agg_program_flow_geo_day`

One date/programme/province:

- rescoring entries;
- rescoring exits;
- net entries minus exits;
- optional persons calculated from current household size, clearly labelled as
  an estimate rather than a historical person count.

### `agg_score_volatility_geo_day`

One date/programme/province/volatility band:

- rescored households;
- households crossing out;
- share of all exits;
- band code, minimum/maximum and band version.

Volatility boundaries belong in versioned configuration, not hardcoded chart
code.

## 9. Critical business decisions before production

These decisions materially change the numbers and must be approved and recorded
in the dataset manifest.

### Decision A — What does an entry or exit mean?

Recommended first-dashboard definition:

- `IN`: score moves from above the programme threshold to at/below it;
- `OUT`: score moves from at/below the threshold to above it.

Call these **rescoring eligibility crossings**, not administrative programme
admissions/removals. Administrative flows should become a separate metric only
after `beneficiaire.csv` event semantics are confirmed.

### Decision B — Which population is evaluated?

The Julia crossing calculation first joins the static ASD/AMOT membership lists.
It therefore measures crossings among households found in the current membership
lists, not all households that could be eligible.

Recommended separation:

| Metric | Population scope |
|---|---|
| Potential programme eligibility | All RSU households with a valid score |
| Rescoring churn among programme members | Current programme membership list |
| Administrative entry/exit | Validated beneficiary-event history |

Store `population_scope` on every eligibility/crossing artifact so these totals
cannot be mixed accidentally.

### Decision C — Which transition/bucket methodology?

There is a reproducibility mismatch in the copied example:

| Configuration | Cutoff | Bucket | Time-series step |
|---|---:|---:|---|
| `raw/parameters/rsu_parameters.json` | 2022-11-23 | 90 days | monthly |
| `prepared/parameters.json` | 2024-03-01 | 30 days | daily |

Therefore, the RAW parameter file alone cannot reproduce the existing prepared
Arrow tables.

Recommended rollout:

1. Define a server-controlled, immutable transformation profile named, for
   example, `julia-compat-30d-v1` using the prepared parameters.
2. Reproduce the Julia outputs with DuckDB and compare exact/aggregate results.
3. Keep the client parameters as source data, but record whether each value was
   accepted, overridden or rejected.
4. If the product requires genuinely weekly movements, define a separate
   `weekly-v1` methodology. Do not label 30-day-bucket crossings as a true
   weekly measurement.
5. Expose the active methodology/version in API metadata and on methodology
   documentation.

### Decision D — Threshold ownership

Current thresholds are AMOT `9.3264284` and ASD `9.743001`. They must be stored
with effective dates and source/version. A new upload must not silently change a
threshold. Either:

- client thresholds must match the approved PostgreSQL configuration; or
- an admin explicitly approves and activates a new threshold version.

Every crossing and eligibility snapshot must record the threshold used.

### Decision E — Volatility bands

Bands such as `20-30`, `30-50` and `51+` are incompatible with a score bounded
approximately between 5 and 15 unless the values mean hundredths/basis points.

Recommended fixed ISE-point bands for an initially comparable chart:

```text
<0.10
0.10-0.25
0.25-0.50
0.50-1.00
1.00-2.00
2.00+
```

Alternatively, use versioned programme-specific empirical percentiles. Whichever
method is approved must be named and versioned.

## 10. PostgreSQL schema additions

Create board-neutral metadata tables rather than putting household analytics in
the existing Macro National fact tables.

### `dataset_batches`

Suggested fields:

- UUID primary key and `board_id`;
- `extract_id`, source system and schema version;
- pipeline and methodology versions;
- status: `uploading`, `queued`, `validating`, `preparing`, `ready`, `failed`,
  `superseded`;
- current processing stage and percentage;
- period start/end and extraction timestamp;
- raw/prepared storage prefixes;
- `is_active`, activated/superseded timestamps;
- creator and failure summary;
- created/started/finished timestamps.

Use a partial unique constraint so only one dataset version is active for a
board/source scope.

### `dataset_files`

One row per RAW logical file:

- batch ID and logical name;
- original filename and object path;
- size, SHA-256 and media type;
- parsed/rejected row counts;
- minimum/maximum dates;
- detected header/schema and validation state.

Unique constraint: `batch_id + logical_name`.

### `dataset_artifacts`

One row per prepared output:

- batch ID, logical artifact name and format;
- object path, checksum and row count;
- schema JSON;
- date range;
- creation timestamp and pipeline version.

### `dataset_quality_checks`

- batch ID;
- stable rule code and rule version;
- severity (`ERROR`, `WARNING`, `INFO`);
- pass/fail status and failed-row count;
- safe summary metadata.

Avoid storing raw household samples in PostgreSQL or validation logs.

### `dataset_program_thresholds`

- batch ID and programme;
- threshold;
- effective dates;
- source and configuration version;
- approval metadata when applicable.

### Job model

For the first implementation, add a dedicated `dataset_import_jobs` table and
reuse the existing repository/worker pattern. This isolates the new large-file
pipeline from the stable XLSX report jobs. A later refactor can generalize both
into one job model after their common behavior is proven.

Workers should continue using PostgreSQL row locking/`SKIP LOCKED` so only one
worker claims a job.

## 11. DuckDB execution and concurrency model

DuckDB should not be a Docker service and should not expose a port. It runs
inside Python worker/API processes.

DuckDB's documented concurrency model allows one read-write process or multiple
read-only processes for a normal database file. Shared/network files require
special caution:

- [DuckDB concurrency](https://duckdb.org/docs/current/connect/concurrency)

Use this model:

1. Only the analytics worker writes.
2. It writes a brand-new version in a staging directory.
3. It closes the DuckDB writer before publication.
4. API processes only open completed versions read-only.
5. PostgreSQL atomically controls which immutable version is active.

Do not let the API and worker mutate the same `.duckdb` file.

In Python:

- create explicit connection objects;
- never use the module-global `duckdb.sql()` connection in concurrent backend
  code;
- create a separate connection per thread/request execution context;
- run synchronous DuckDB work in a bounded thread pool from FastAPI;
- parameterize values and allowlist columns/granularity;
- set `memory_limit`, `threads`, `temp_directory` and maximum spill size.

DuckDB documents that its global Python connection is not thread-safe:

- [DuckDB Python connection guidance](https://duckdb.org/docs/stable/clients/python/overview)

### Local Docker deployment

Add an `analytics` named volume:

- analytics worker: `/data/analytics` read-write;
- API: `/data/analytics` read-only;
- worker-only temporary/spill directory with sufficient disk.

### Multi-host production deployment

Do not place a mutable `.duckdb` database on NFS. Store immutable Parquet/Arrow
in object storage and either:

- query a controlled local cache per API instance; or
- introduce a dedicated analytics service later if load requires it.

The first production version should stage the active immutable generation into
a local read-through cache instead of depending on unpinned runtime extensions.

## 12. API design

### Dataset lifecycle endpoints

```text
POST /api/boards/programmes-sociaux-rescoring/datasets/init
POST /api/boards/programmes-sociaux-rescoring/datasets/{id}/complete
GET  /api/boards/programmes-sociaux-rescoring/datasets/{id}/status
GET  /api/boards/programmes-sociaux-rescoring/datasets/{id}/validation
GET  /api/boards/programmes-sociaux-rescoring/datasets/active
POST /api/boards/programmes-sociaux-rescoring/datasets/{id}/activate
POST /api/boards/programmes-sociaux-rescoring/datasets/{id}/rollback
```

For an MVP direct-stream upload, `init` and `complete` may be combined into one
multipart endpoint. Keep the internal dataset lifecycle unchanged so direct
object-store upload can replace it later.

### Dashboard endpoints

```text
GET /api/boards/programmes-sociaux-rescoring/filters
GET /api/boards/programmes-sociaux-rescoring/dashboard
```

Dashboard query parameters:

- `program=ALL|ASD|AMO_TADAMON`;
- `regionId`;
- `provinceId`;
- `startDate`;
- `endDate`;
- `grain=WEEK|MONTH|QUARTER`.

A single dashboard endpoint is appropriate for this one-page view because it
can calculate all panels in one DuckDB query session and avoid several browser
round trips.

Suggested response:

```json
{
  "meta": {
    "datasetId": "...",
    "pipelineVersion": "...",
    "methodologyVersion": "...",
    "populationScope": "...",
    "coverage": {"start": "...", "end": "..."}
  },
  "appliedFilters": {},
  "kpis": {},
  "flows": [],
  "volatility": [],
  "territories": []
}
```

Use an ETag derived from dataset ID plus normalized filters. A short bounded
cache can be added only after correctness is established.

## 13. Suggested code organization

```text
apps/api/
  analytics/
    __init__.py
    config.py                 DuckDB/resource settings
    contracts.py              RAW file schemas and versions
    manifest.py               manifest/checksum handling
    storage.py                streaming/versioned dataset storage
    models.py                 PostgreSQL dataset metadata models
    repository.py             jobs, versions, activation and rollback
    validation.py             structural and cross-file rules
    engine.py                 explicit DuckDB connection factory
    pipeline.py               stage orchestration
    publication.py            manifest, _SUCCESS and atomic activation
    sql/
      001_bronze.sql
      010_dimensions.sql
      020_scores.sql
      030_transitions.sql
      040_crossings.sql
      050_eligibility.sql
      060_marts.sql
      090_reconciliation.sql
    worker.py
  boards/programmes_sociaux_rescoring/
    router.py
    schemas.py
    service.py
    queries.py
```

Keep transformation SQL version-controlled and readable. Do not hide important
threshold/bucketing rules in Pandas operations or dashboard TypeScript.

## 14. Configuration and Docker changes

### Python dependencies

Add and pin tested versions of:

- `duckdb`;
- `pyarrow`.

Pin versions after running compatibility tests; do not use floating `latest`
versions. DuckDB storage compatibility depends on the reader/writer versions:

- [DuckDB storage versions](https://duckdb.org/docs/stable/internals/storage)

### Settings

Suggested environment variables:

```text
ANALYTICS_LOCAL_PATH=/data/analytics
ANALYTICS_MAX_UPLOAD_SIZE_MB=1024
DUCKDB_MEMORY_LIMIT=4GB
DUCKDB_THREADS=4
DUCKDB_TEMP_DIRECTORY=/data/analytics/tmp
DUCKDB_MAX_TEMP_DIRECTORY_SIZE=20GB
ANALYTICS_QUERY_TIMEOUT_SECONDS=30
ANALYTICS_PIPELINE_VERSION=rescoring-v1
ANALYTICS_EXPORT_ARROW=true
```

Values must be adjusted to the deployment resources. DuckDB exposes memory,
thread and temporary-storage controls:

- [DuckDB configuration](https://duckdb.org/docs/stable/configuration/overview)

### Compose

Recommended services/volume changes:

```text
api:
  mount analytics volume read-only

analytics-worker:
  same API image
  command python -m analytics.worker
  mount analytics volume read-write
  depends on healthy PostgreSQL

analytics volume:
  stores local immutable generations and worker spill
```

Keeping a separate analytics worker avoids blocking the lighter XLSX report
worker and allows independent CPU/memory limits.

## 15. Data-quality rules

### Blocking rules

- required file or required column missing;
- unsupported RAW schema version;
- invalid parameter JSON;
- missing or duplicate ASD/AMOT threshold;
- primary identifier missing or nonnumeric;
- conflicting rows sharing a supposedly unique score/household ID;
- province mapped to more than one region;
- unparseable score dates;
- no valid score events;
- invalid/uncovered volatility-band definition;
- failed detail-to-aggregate reconciliation.

### Quarantine or warning rules

- exact duplicate rows;
- scores outside the configured floor/cap;
- unknown request type;
- score, programme or beneficiary rows without a household reference;
- missing household size or geography;
- unknown beneficiary motif;
- unexpectedly large row-count/date-range movement from the active dataset;
- households present in more than one programme when this is allowed but affects
  distinct-person/household totals.

### Why these checks are necessary

The copied sample already contains:

| Observation | Verified count |
|---|---:|
| Household rows | 499,999 |
| Distinct household IDs | 479,079 |
| Score rows | 1,903,133 |
| Distinct score IDs | 1,824,221 |
| Score rows outside 5-15 | 244 |
| Score rows without household match | 7 |
| Beneficiary rows without household match | 3 |
| Distinct households appearing in both ASD and AMOT lists | 280,301 |

Duplicates must be separated into exact duplicates versus conflicting duplicate
IDs. Programme `ALL` KPIs must not blindly add ASD and AMOT distinct-household
counts because of the overlap.

### Required reconciliation checks

- every crossing satisfies its exact IN/OUT rule;
- every daily aggregate equals its detailed crossing source;
- region totals equal province totals plus explicit unknown geography;
- sum of volatility bands equals the relevant transition population;
- `eligible_after_threshold <= evaluated_households`;
- no negative counts;
- person totals reconcile to household-size sums and disclose missing-size
  coverage;
- snapshot values are never summed across snapshot dates.

## 16. Idempotency, activation and rollback

Calculate a deterministic version fingerprint from:

```text
ordered RAW file checksums
+ parameter checksum
+ RAW schema version
+ pipeline/transformation version
+ cutoff and bucket configuration
+ threshold version
+ volatility-band version
```

Required behavior:

- same inputs and same configuration: return/reuse the successful generation;
- same inputs and new transformation version: build a new generation;
- failed generation: never activate;
- successful generation: activate in one PostgreSQL transaction;
- API reads only the active publication;
- rollback changes the PostgreSQL active pointer, not the data files;
- retry writes to a new staging area or safely resumes documented stages;
- no active file is modified in place.

Raw and prepared objects remain immutable until retention policy permits removal.
The `.duckdb` snapshot is rebuildable; RAW plus pipeline version and parameters
are the recovery source.

## 17. Full rebuild first; incremental processing later

The current client files behave mainly as complete snapshots, not reliable
change-data feeds. At roughly 4.23 million source rows, a deterministic full
rebuild is the safest version-one strategy.

Only introduce incremental processing when the client supplies stable semantics:

- score events: stable score ID and late-arrival behavior;
- household data: `updated_at` or dated snapshots;
- programme membership: explicit membership snapshot date;
- beneficiary events: stable event ID and confirmed state-transition semantics;
- geography and household size: effective dates if history must reflect old
  values.

Possible future incremental rules:

- upsert score events by score ID;
- recompute transitions for every household affected by a new/changed score;
- recompute the following transition when a late event is inserted;
- diff dated programme-membership snapshots;
- force a full rebuild whenever thresholds, cutoff, bucket method, score bounds
  or volatility bands change.

The current Julia bucket anchor depends on the earliest loaded score date. Adding
an older late event can move all bucket boundaries. For a stable future
incremental methodology, use a documented fixed calendar/epoch anchor.

## 18. Selected-period correctness

For a dashboard request from `startDate` to `endDate`:

- filter completed transitions by transition/crossing date;
- retain the score immediately before `startDate` when calculating a transition
  that occurs inside the period;
- calculate eligibility from the latest score on or before `endDate`;
- never sum multiple eligibility snapshots;
- filter programme, region and province before final aggregation;
- use the same underlying event population for week/month/quarter display
  aggregation.

This prevents the first in-period transition from disappearing because its
previous score occurred before the selected period.

## 19. Security and privacy

Although household IDs are anonymized, this remains sensitive social-programme
data.

Required controls:

- encryption in transit and at rest;
- least-privilege object-storage and PostgreSQL service accounts;
- admin/editor import permissions and viewer read permissions;
- read-only analytics mount in the API container;
- no RAW rows or household identifiers in logs;
- validation reports contain counts and safe summaries, not exposed samples;
- archive/file path allowlists;
- parameterized SQL and allowlisted grouping fields;
- no arbitrary SQL endpoint;
- no unsigned or unnecessary DuckDB extensions;
- retention/deletion workflow with audit entry;
- separate backup/restore tests for PostgreSQL metadata and RAW/prepared objects.

DuckDB runs with the backend process's file privileges, so path and SQL controls
are important:

- [Securing DuckDB](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview)

PostgreSQL is the correct concurrent transactional store because its transaction
and MVCC model is designed for simultaneous application activity:

- [PostgreSQL transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [PostgreSQL concurrency control](https://www.postgresql.org/docs/current/mvcc.html)

## 20. Testing strategy

### Fast CI fixture

Create a tiny deterministic RAW fixture with approximately 50-200 households
covering:

- ASD only, AMOT only, both and neither;
- no crossing, IN crossing and OUT crossing exactly at threshold;
- corrected versus calculated score;
- missing geography and household size;
- duplicate and malformed rows;
- a score before the requested period and a crossing inside it.

### Test layers

1. Contract tests for every RAW schema and manifest version.
2. Unit tests for normalization, thresholds, bucket boundaries and bands.
3. SQL tests for transitions, crossings, snapshots and geography.
4. Reconciliation tests between detail facts and marts.
5. PostgreSQL migration/repository tests.
6. Idempotency, duplicate upload, failed publication and rollback tests.
7. Concurrent job-claim tests.
8. API filter/authorization/response-contract tests.
9. Frontend end-to-end upload, status, filtering and no-data tests.
10. Security tests for ZIP traversal, excessive expansion and invalid paths.

### Julia parity suite

Use the copied prepared Arrow generation as a golden reference:

- freeze the exact prepared parameter profile;
- compare row counts and schemas;
- compare score transitions and crossings on a deterministic subset;
- compare programme/date/zone totals;
- document intentional differences rather than weakening tests.

The full 493 MB local copy should be used for manual/nightly acceptance and
performance tests, not ordinary pull-request CI. CI must provision PostgreSQL,
run Alembic migrations and execute the integration suite.

## 21. Phased implementation plan

### Phase 0 — Approve semantics and contracts

Deliverables:

- approved RAW ZIP/manifest contract;
- programme population-scope decision;
- eligibility denominator definition;
- administrative versus rescoring terminology;
- threshold ownership/effective-date policy;
- transition methodology and volatility bands;
- `julia-compat-30d-v1` profile.

Exit criterion: two engineers can independently calculate the same expected
crossing from the written rules.

### Phase 1 — Platform foundation

Deliverables:

- pinned DuckDB/PyArrow dependencies;
- analytics settings and connection factory;
- analytics volume and separate worker service;
- PostgreSQL migration for batches, files, artifacts, quality and jobs;
- explicit data contracts and tiny fixture.

Exit criterion: worker can claim a dataset job and create an isolated staging
generation without touching the Macro National pipeline.

### Phase 2 — Streaming landing and validation

Deliverables:

- safe ZIP upload/extraction;
- streaming SHA-256 and size limits;
- manifest and structural validation;
- explicit DuckDB CSV schemas;
- rejects/quarantine and validation endpoint;
- idempotent content fingerprint.

Exit criterion: valid sample is queued; corrupted, unsafe or schema-invalid
bundles fail with actionable messages without high memory buffering.

### Phase 3 — RAW-to-prepared transformation

Deliverables:

- dimensions and normalized score/programme/beneficiary facts;
- transitions and crossings;
- eligibility snapshots;
- daily flow and volatility marts;
- Parquet exports and optional Arrow exports;
- manifest and reconciliation suite.

Exit criterion: DuckDB results meet the approved Julia parity tolerances and all
blocking reconciliations pass.

### Phase 4 — Immutable publication and rollback

Deliverables:

- `_SUCCESS` publication contract;
- artifact registration;
- transactional activation/supersession;
- rollback and retention workflow;
- read-only API access to the active generation.

Exit criterion: a failed generation leaves the old dashboard unchanged; rollback
switches versions without rebuilding.

### Phase 5 — Dashboard API

Deliverables:

- filters endpoint;
- combined dashboard endpoint;
- programme/region/province/date/grain validation;
- dataset/methodology metadata in every response;
- bounded execution and query instrumentation.

Exit criterion: all KPI/chart/table totals reconcile to prepared marts for every
supported filter combination.

### Phase 6 — Frontend integration

Deliverables:

- new RAW dataset upload/status/validation UI;
- removal of hardcoded dashboard arrays;
- programme, region, dependent province and date filters;
- weekly/monthly/quarterly grouping;
- loading, failure, no-data and stale-version states;
- visible data/reference/methodology information.

Exit criterion: end-to-end test imports a fixture and proves every visible panel
changes consistently with filters.

### Phase 7 — Production hardening

Deliverables:

- direct/resumable object-storage upload;
- backups and restore drill;
- resource limits, structured metrics and alerts;
- retention and deletion policy;
- security review;
- performance/load tests and operations runbook.

Exit criterion: documented recovery, rollback, capacity and incident procedures
have been exercised.

## 22. Decisions for the next follow-up

Recommended defaults are shown in the final column.

| Decision | Options | Recommended starting point |
|---|---|---|
| Upload delivery | ZIP, browser folder, direct object-store session | ZIP for MVP; resumable object storage for production |
| Durable prepared format | Arrow only, Parquet only, both | Parquet canonical + optional Arrow exports |
| Programme entry/exit | Threshold crossing, administrative movement | Threshold crossing, explicitly labelled rescoring |
| Eligibility population | All valid-scored households, current members | Report both separately; never mix |
| Transition method | Julia 30-day, raw event, calendar week | Julia parity first; approve separate weekly method |
| Threshold changes | Trust each upload, server-approved version | Server-approved/effective-dated version |
| Initial processing | Incremental, full rebuild | Immutable full rebuild |
| DuckDB access | Shared mutable DB, immutable read-only version | Immutable read-only version |
| Analytics query result | Arrow to browser, aggregated JSON | Aggregated JSON; Arrow only for internal/export use |

## 23. What not to do

- Do not create a DuckDB network service or port.
- Do not store 1.9 million score events in PostgreSQL merely for analytics.
- Do not share one mutable `.duckdb` file between API and worker processes.
- Do not make Arrow IPC the only recoverable prepared representation.
- Do not infer production CSV types from a small sample.
- Do not load a 272+ MB upload fully into FastAPI/Next.js memory.
- Do not overwrite active data files in place.
- Do not silently mix all-household eligibility with current-member crossings.
- Do not describe threshold crossings as administrative exits.
- Do not permit arbitrary SQL, filenames, partitions or sort expressions from
  frontend input.

## 24. Definition of success

The architecture is ready for production when:

1. A client RAW bundle can be uploaded without full-memory buffering.
2. Every source file and prepared artifact is checksummed and versioned.
3. Invalid data produces a specific validation report and never activates.
4. The DuckDB pipeline deterministically reproduces the approved methodology.
5. PostgreSQL activates a generation atomically and can roll it back.
6. The API reads immutable analytics data and supports programme, region,
   province and selected-period filters.
7. Dashboard totals reconcile to detailed facts.
8. The active dataset, threshold, population scope and methodology are visible
   and auditable.
9. The Macro National dashboard remains unaffected.
10. Backup, restore, retention and security procedures are tested.
