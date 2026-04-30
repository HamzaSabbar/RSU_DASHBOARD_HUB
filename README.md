# RSU Dashboard Hub

Authenticated web workspace hosting the **Macro National** RSU weekly dashboard. Admins upload one French Excel workbook through the UI; the API stores the raw file and creates a queued report job, a separate worker validates/parses/calculates the workbook, and the web dashboard renders the latest succeeded dashboard JSON.

## Stack

- **Web**: Next.js 14 (App Router) + TypeScript strict + Tailwind + shadcn-style primitives + Recharts + NextAuth v5 (Credentials)
- **API**: FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2 + Pandas + openpyxl + Google Cloud Storage
- **DB**: PostgreSQL 16
- **Infra**: Docker Compose (services `db`, `api`, `worker`, `web`). Dev-mode hot reload via `docker-compose.override.yml`.

## Running locally

Requirements: Docker Desktop 4.25+ with Compose v2.

```bash
cp .env.example .env
# edit .env: set a random NEXTAUTH_SECRET (openssl rand -base64 32),
# the ADMIN_EMAIL + ADMIN_PASSWORD you will use, and optionally
# change POSTGRES_PASSWORD.
docker compose up --build
```

Then open:

- Web UI: http://localhost:3000
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health

Log in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` values from `.env`.

### Dev vs. prod compose

`docker compose up` reads both `docker-compose.yml` and `docker-compose.override.yml`. The override bind-mounts source directories and runs `uvicorn --reload` / `next dev`, so file changes are live. For a prod-like image run:

```bash
docker compose -f docker-compose.yml up --build
```

### Resetting state

```bash
docker compose down -v            # drops the dbdata volume (tables + seed data)
rm -rf data/uploads/*             # drops stored xlsx files
rm -rf data/storage/*             # drops report job artifacts when using local storage
docker compose up --build         # re-seeds admin + boards, re-runs migrations
```

## Admin seeding

On first startup the API lifespan:

1. Runs `alembic upgrade head`.
2. Upserts a `users` row for `ADMIN_EMAIL` with a bcrypt hash of `ADMIN_PASSWORD`.
3. Upserts a `boards` row for `macro-national` (idempotent on the slug).

Change the admin password by editing `.env` and restarting, but note: the lifespan does not re-hash an existing user. To rotate, truncate the user via psql or reset the volume.

## Uploading data

In the Macro National dashboard, click "Charger des données" and upload one French `.xlsx` workbook. The API accepts the file, stores it, creates a queued job, and returns a job ID. The `worker` service validates the workbook, writes computed artifacts, ingests normalized rows into cumulative Postgres fact tables, and marks the job `succeeded` or `failed`. The Macro National page renders dashboard JSON from active cumulative facts using the selected date interval. It does **not** generate PDFs.

Each successful workbook becomes an active upload batch keyed by `id_chargement` from `01_Parametres`. If another workbook uses the same `id_chargement`, the API returns `409` until the user confirms replacement. Replacement keeps the old raw file and generated artifacts for audit, marks the old batch as superseded, and excludes its facts from future dashboard queries.

### Storage configuration

Local development defaults to local object storage:

```env
STORAGE_DRIVER=local
STORAGE_LOCAL_PATH=/data/storage
GCS_PREFIX=rsu-dashboard
REPORT_MAX_UPLOAD_SIZE_MB=50
REPORT_JOB_REPOSITORY=db
REPORT_WORKER_POLL_SECONDS=2
```

For Google Cloud Storage:

```env
STORAGE_DRIVER=gcs
GCS_BUCKET_NAME=my-rsu-dashboard-bucket
GCS_PREFIX=rsu-dashboard
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

If `STORAGE_DRIVER=gcs` is set but GCS credentials or bucket configuration are missing locally, the API falls back to local storage. Artifacts are written under:

- raw upload: `rsu-dashboard/uploads/{jobId}/input.xlsx`
- normalized parsed data: `rsu-dashboard/jobs/{jobId}/normalized.json`
- validation result: `rsu-dashboard/jobs/{jobId}/validation.json`
- dashboard result: `rsu-dashboard/jobs/{jobId}/dashboard.json`

Job metadata is stored in Postgres by default through `REPORT_JOB_REPOSITORY=db`. For isolated local experiments, `REPORT_JOB_REPOSITORY=local` stores job records in `report_jobs.json` under `STORAGE_LOCAL_PATH`; this is not intended for production. `REPORT_WORKER_POLL_SECONDS` controls how often the worker checks for queued jobs.

When using the DB repository, cumulative facts are stored in typed tables for regions, provinces, codes, RSU stock/flows, ASD, AMO Tadamon, FMS treatment, blocked households, and amount rules. Dashboard requests query these indexed tables instead of reparsing previous workbooks.

### Required workbook sheets

Required:

`01_Parametres`, `02_Regions`, `03_Provinces`, `04_Codes`, `10_RSU`, `20_ASD`, `30_AMO_Tadamon`, `40_FMS`

Optional:

`00_Guide`, `50_Regles_Montant`

Tables are found by header names, not fixed cell coordinates. Unknown extra columns are accepted and reported as warnings. Validation messages are returned in French with severity, sheet, section, row, column, code, and message.

### Detailed workbook template

The uploaded file must be a single `.xlsx` workbook. The server reads source data only; dashboard KPIs, percentages, trends, rankings, and formatted display values are calculated by the worker.

General rules:

- Keep sheet names exactly as documented below.
- Keep column header names stable. The parser finds each section by its header row, so sections may move within a sheet as long as the required headers remain present.
- Dates may be Excel dates or ISO strings such as `2026-03-17`.
- Month fields use `AAAA-MM`, for example `2026-03`.
- Numeric fields must be numeric and non-negative.
- Extra unknown columns are accepted but returned as warnings.
- `id_chargement` is the business upload ID. It must be present in `01_Parametres` and is rejected as a duplicate unless the upload uses `replace=true`.
- Reference values are validated against `02_Regions`, `03_Provinces`, and `04_Codes`.
- Example rows whose `id_chargement` starts with `EXAMPLE_` are sample data and should be replaced before production uploads.

#### `00_Guide` optional

Human-readable guide sheet. It is ignored by the parser.

#### `01_Parametres` required

One active row per workbook. This row controls the reporting period, current reporting month, trend method, and RSU chart unit.

Required columns:

```text
id_chargement
version_fichier
date_rapport
debut_periode
fin_periode
date_reference_donnees
date_heure_extraction
systeme_source
code_langue
mois_reporting_courant
indicateur_mois_partiel
suffixe_libelle_mois_partiel
type_unite_graphique_rsu
methode_tendance
utiliser_regles_montant_secours
charge_par
commentaires
```

Important values:

- `type_unite_graphique_rsu`: usually `MENAGES` or `PERSONNES`.
- `methode_tendance`: `REGRESSION_LINEAIRE`, `MOYENNE_MOBILE`, or `AUCUNE`.
- `indicateur_mois_partiel`: boolean; when true, the worker appends `suffixe_libelle_mois_partiel` to the current month label.

#### `02_Regions` required

Reference list used to validate region codes and order regional charts.

Required columns:

```text
code_region
nom_region
ordre_affichage
```

The sample template may include `actif`; it is not used by the API and is reported as an unknown-column warning.

#### `03_Provinces` required

Reference list used to validate provinces and make sure each province belongs to the supplied region.

Required columns:

```text
code_region
nom_province
```

Optional accepted column:

```text
ordre_affichage
```

The sample template may include `cle_province` and `nom_region`; they are not used by the API and are reported as unknown-column warnings.

#### `04_Codes` required

Controlled values used by strict validation.

Accepted canonical columns:

```text
type_code
code
libelle
ordre_affichage
```

Accepted aliases:

- `nom_champ` for `type_code`
- `description` for `libelle`

Common code domains:

```text
code_registre: RNP, RSU
type_unite: MENAGES, PERSONNES
mode_source: NOUVEAUX_DIRECTS, DIFF_SNAPSHOT_CUMULE
methode_tendance: REGRESSION_LINEAIRE, MOYENNE_MOBILE, AUCUNE
code_type_famille: INDIVIDUEL, MARIES_AVEC_ENFANTS, MONOPARENTAL, MULTI_NOYAU, TOUS
code_niveau_risque: ELEVE, MOYEN
code_perimetre_programme: ASD, AMO_TADAMON, LES_DEUX, UNKNOWN
code_motif_blocage: FMS_FRAUD, PROCEDURE_MULTI_NOYAU, PROCEDURE_INDIVIDUEL
unite_beneficiaire: MENAGE, PERSONNE
type_montant: MONTANT_BASE, MONTANT_MOYEN
```

The workbook can add more controlled values later as long as rows are consistent and referenced codes exist.

#### `10_RSU` required

Contains RNP/RSU stock snapshots, monthly registration flows, and chart annotations.

Section A, stock RNP/RSU:

```text
id_chargement
date_reference
code_registre
type_unite
total_cumule
systeme_source
commentaires
```

Required stock combinations:

- `RNP` / `PERSONNES`
- `RSU` / `MENAGES`
- `RSU` / `PERSONNES`

Section B, nouvelles inscriptions RSU:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
type_unite
nb_nouvelles_inscriptions
mode_source
systeme_source
commentaires
```

Section C, annotations RSU:

```text
code_graphique
mois_evenement
libelle_annotation
commentaires
```

Stock rows are snapshots and are not accumulated week after week. Flow rows are event data and are aggregated by month, region, province, and unit.

#### `20_ASD` required

Contains ASD stock, entrants/sortants, rescoring exits, and fraud radiations.

Section A, stock ASD:

```text
id_chargement
date_reference
type_unite
nb_actifs
systeme_source
commentaires
```

Required stock combinations:

- `MENAGES`
- `PERSONNES`

Section B, flux entrants/sortants ASD:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
nb_entrants_menages
nb_sortants_menages
nb_entrants_personnes
nb_sortants_personnes
montant_mensuel_entrants_dh
montant_mensuel_sortants_dh
systeme_source
commentaires
```

Section C, rescoring ASD:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
nb_sortants_menages
nb_sortants_personnes
nb_menages_non_communiques
montant_mensuel_arrete_dh
systeme_source
commentaires
```

Section D, radiation pour fraude ASD:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
radiated_hh_count
radiated_persons
montant_mensuel_arrete_dh
systeme_source
commentaires
```

Accepted aliases:

- `nb_menages_radies` for `radiated_hh_count`
- `nb_personnes_radiees` for `radiated_persons`

#### `30_AMO_Tadamon` required

Same structure as `20_ASD`, but for AMO Tadamon. The worker uses this sheet for AMO stock, AMO flows, combined ASD + AMO regional flows, rescoring savings, and fraud savings.

Section A, stock AMO Tadamon:

```text
id_chargement
date_reference
type_unite
nb_actifs
systeme_source
commentaires
```

Required stock combinations:

- `MENAGES`
- `PERSONNES`

Section B, flux entrants/sortants AMO Tadamon:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
nb_entrants_menages
nb_sortants_menages
nb_entrants_personnes
nb_sortants_personnes
montant_mensuel_entrants_dh
montant_mensuel_sortants_dh
systeme_source
commentaires
```

Section C, rescoring AMO Tadamon:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
nb_sortants_menages
nb_sortants_personnes
nb_menages_non_communiques
montant_mensuel_arrete_dh
systeme_source
commentaires
```

Section D, radiation pour fraude AMO Tadamon:

```text
id_chargement
debut_periode
fin_periode
date_evenement
mois_evenement
code_region
nom_province
radiated_hh_count
radiated_persons
montant_mensuel_arrete_dh
systeme_source
commentaires
```

Accepted aliases:

- `nb_menages_radies` for `radiated_hh_count`
- `nb_personnes_radiees` for `radiated_persons`

#### `40_FMS` required

Contains Fraud Management System treatment results and blocked-household snapshots.

Section A, traitement FMS:

```text
id_chargement
date_reference
code_type_famille
code_niveau_risque
code_perimetre_programme
code_region
nom_province
demandes_injectees
demandes_traitees
doute_confirme
doute_leve
en_attente
systeme_source
commentaires
```

Validation checks:

- `demandes_traitees <= demandes_injectees`
- `doute_confirme + doute_leve <= demandes_traitees`
- `en_attente` should be close to `demandes_injectees - demandes_traitees`; inconsistent values are warnings.

Section B, ménages bloqués:

```text
id_chargement
date_reference
code_motif_blocage
code_type_famille
code_region
nom_province
nb_menages_bloques
nb_personnes_bloquees
systeme_source
commentaires
```

Blocked-household rows are current stock snapshots and are not accumulated across weekly uploads.

#### `50_Regles_Montant` optional

Fallback monthly amount rules used only when direct stopped-benefit amounts are missing from ASD or AMO Tadamon rescoring/fraud rows.

Columns:

```text
code_programme
date_effet_debut
date_effet_fin
code_type_famille
unite_beneficiaire
type_montant
montant_mensuel_dh
facteur_annualisation
commentaires
```

Supported `code_programme` values are normally `ASD` and `AMO_TADAMON`. Use `code_type_famille = TOUS` for a generic fallback rule.

### Endpoints

All examples assume you already have a FastAPI JWT in `TOKEN`.

```bash
curl -X POST "http://localhost:8000/api/reports/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@rapport_rsu.xlsx"
```

Response:

```json
{
  "jobId": "8e0b5a1b-...",
  "status": "queued",
  "statusUrl": "/api/reports/jobs/8e0b5a1b-.../status",
  "dashboardUrl": "/api/reports/jobs/8e0b5a1b-.../dashboard",
  "validationUrl": "/api/reports/jobs/8e0b5a1b-.../validation"
}
```

Duplicate `id_chargement` values from `01_Parametres` are rejected by default with a structured `409` response:

```json
{
  "detail": {
    "code": "DUPLICATE_ID_CHARGEMENT",
    "idChargement": "LOAD-2026-W11",
    "message": "Un chargement avec cet id_chargement existe déjà. Confirmez le remplacement pour écraser la version active."
  }
}
```

To intentionally replace the active business upload:

```bash
curl -X POST "http://localhost:8000/api/reports/jobs?replace=true" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@rapport_rsu.xlsx"
```

Poll status:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/jobs/{jobId}/status"
```

Statuses are `queued`, `running`, `succeeded`, and `failed`.

Fetch validation:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/jobs/{jobId}/validation"
```

Fetch the job-specific dashboard/debug JSON after success:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/jobs/{jobId}/dashboard"
```

If the job is still queued/running or failed, the job dashboard endpoint returns a useful `409` response with the job status and validation URL.

Fetch the cumulative dashboard rendered by `/dashboard/macro-national`:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/dashboard?startDate=2026-04-01&endDate=2026-04-30"
```

If no date parameters are supplied, the API uses the latest active upload batch period.

Fetch available date-filter metadata:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/reports/available-periods"
```

### Dashboard response shape

The API computes dashboard KPIs server-side from the workbook and returns raw and formatted values:

```json
{
  "meta": {
    "jobId": "...",
    "idChargement": "...",
    "titreRapport": "Tableau de bord hebdomadaire de suivi RSU",
    "dateRapport": "2026-04-24",
    "dateReferenceDonnees": "2026-04-20",
    "locale": "fr-MA",
    "moisReportingCourant": "2026-04",
    "moisPartiel": true,
    "dateRange": {
      "startDate": "2026-04-01",
      "endDate": "2026-04-30"
    }
  },
  "cards": {
    "inscriptions": {},
    "programmesSociaux": {},
    "traitementFms": {},
    "resultatFms": {},
    "radiationFraude": {},
    "rescoring": {},
    "economieBudgetaire": {}
  },
  "charts": {
    "rsuInscriptionsMensuelles": {},
    "asdEntreesSorties": {},
    "fmsMatriceRisque": {},
    "menagesBloquesNational": {},
    "fluxRegionauxAsdAmot": {},
    "menagesBloquesRegionaux": {}
  },
  "tables": {
    "rsuEvolution": [],
    "asdEvolution": [],
    "topProvincesFlux": [],
    "topProvincesBloquees": []
  },
  "footnotes": [],
  "validationSummary": { "errors": 0, "warnings": 0, "infos": 0 }
}
```

The response includes French labels, French number/percent formatting, compact `k`/`M` displays, annual savings in `M Dhs/an` or `MM Dhs/an`, region order from `02_Regions`, and color hints for positive, risk, exit, and neutral values.

## Running tests

```bash
docker compose exec api pytest -q       # analytics + report pipeline tests
docker compose exec api ruff check .    # lint
docker compose exec web npm run lint
docker compose exec web npm run typecheck
```

End-to-end (Playwright) runs against the live compose stack:

```bash
docker compose up -d
cd apps/web
npm install
npx playwright install --with-deps chromium
npx playwright test
```

## Adding a new board

The board pattern is a Python package plus a matching Next.js route folder. Ten-step recipe:

1. Pick a slug, e.g. `regional-ouest`. It becomes both the Python package name (`regional_ouest`, underscores) and the URL segment.
2. Create `apps/api/boards/regional_ouest/` with an empty `__init__.py`, `schemas.py`, `parser.py`, `analytics.py`, `service.py`, `router.py`, and `spec.py`.
3. In `schemas.py`, define a `FileKind` enum, `EXPECTED_FILES` list, and the Pydantic payload root.
4. In `parser.py`, write one parser per file kind plus a `detect_file_kind(filename, content)` function.
5. In `analytics.py`, write pure DataFrame-to-Pydantic functions.
6. In `service.py`, mirror the Macro National service: `persist_upload`, `recompute_snapshot`, `get_latest_payload`.
7. In `router.py`, expose `GET /data` and `POST /upload`.
8. In `spec.py`, export `BOARD_SPEC = BoardSpec(slug="regional-ouest", title=..., description=..., expected_files=EXPECTED_FILES, router=router)`.
9. In `__init__.py`, add `from boards.regional_ouest.spec import BOARD_SPEC`.
10. Create `apps/web/app/(app)/dashboard/regional-ouest/page.tsx` plus a mirror TypeScript type at `apps/web/lib/types/regional-ouest.ts`. Upsert the board row by adding `{"slug": "regional-ouest", "title": ..., "description": ...}` to `BOARDS_SEED` in `apps/api/main.py`.

Restart the api container. `GET /api/boards` auto-discovers the new board via `pkgutil.iter_modules`, the hub renders a new card, and the router is auto-mounted at `/api/boards/regional-ouest/*`.

## Architecture notes

- **Auth handshake**: NextAuth's Credentials `authorize()` POSTs to the FastAPI `/api/auth/login`, which returns a JWT signed with `NEXTAUTH_SECRET` (HS256). The session callback stores that token; server-side fetches in `lib/api.ts` inject `Authorization: Bearer`. FastAPI decodes the same JWT with the same secret via `get_current_user`.
- **Report uploads**: browser posts multipart to the thin Next.js proxy route (`/api/reports/jobs`) that forwards to FastAPI with the Bearer header. FastAPI stores the raw workbook and creates a queued report job.
- **Worker processing**: the `worker` service claims queued jobs, parses and validates the workbook, writes normalized data, validation JSON, and job dashboard JSON to the configured storage driver, ingests active facts into Postgres, then marks the job `succeeded` or `failed`.
- **Dashboard rendering**: `/dashboard/macro-national` fetches `/api/reports/dashboard?startDate=...&endDate=...` and renders cumulative active facts for the selected interval.
- **Audit**: every login writes a row in `audit_log` with a JSONB metadata column.

## Out of scope (v1)

- Multi-tenancy / orgs
- Email-based password reset
- Viewer/editor roles (the `role` column is there for future use)
- Websockets / live updates
- PDF export of the dashboard (TODO)

## CI

`.github/workflows/ci.yml` runs two jobs:

- **api**: `pip install -r requirements.txt`, `ruff check .`, `pytest -q`.
- **web**: `npm ci`, `npm run lint`, `npm run typecheck`.

This repo has no GitHub remote at the time of writing, so the workflow has been authored but not verified green. Push the repo to GitHub to exercise it.

### Known issue: `npm run build`

A `next build` currently fails while prerendering the legacy `/_error: /404` and `/_error: /500` pages router fallbacks (`TypeError: Cannot read properties of null (reading 'useContext')` out of one of Next's compiled internal chunks). The App Router pages, middleware, dev server (`next dev`), and prod server (`next start`) all work end-to-end. The CI job currently runs lint + typecheck + pytest; `npm run build` is left commented in `ci.yml` and should be re-enabled once the fallback-prerender bug is resolved. Workarounds to explore: pinning Next 14.1.x, or dropping `output: "standalone"` in favor of a plain `next start` image.
