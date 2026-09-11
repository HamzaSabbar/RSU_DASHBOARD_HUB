# RSU Dashboard Hub

Authenticated dashboard for the 18 RSU (Registre Social Unifié) process KPIs:
import an Excel workbook, browse KPIs by process family or all at once,
filter by period/region/province/milieu, and export a PDF report.

## Stack

- **Web**: Next.js 14 (App Router) + TypeScript + Tailwind + Recharts + NextAuth v4 (Credentials)
- **API**: FastAPI + SQLAlchemy 2 (async) + Alembic + Pydantic v2 + Pandas/openpyxl
- **DB**: PostgreSQL, run locally (no Docker)

## Running locally

Requirements: Python 3.11+, Node 18+, PostgreSQL installed locally.

### 1. Database

Point `DATABASE_URL` / `DATABASE_URL_SYNC` in `.env` at a local Postgres
instance (see `.env.example`). If you don't already have a cluster running,
initialize and start one, e.g.:

```bash
initdb -D .pgdata_local -U postgres
pg_ctl -D .pgdata_local -l .pgdata_local/server.log start
```

Then create the database/role from `.env` (`POSTGRES_USER` /
`POSTGRES_PASSWORD` / `POSTGRES_DB`) with `psql` or `createdb`/`createuser`.

### 2. API

```bash
cd apps/api
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../../.env.example ../../.env     # edit DATABASE_URL, NEXTAUTH_SECRET, ADMIN_EMAIL/PASSWORD
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```

On startup the API upserts an admin user from `ADMIN_EMAIL`/`ADMIN_PASSWORD`.

### 3. Web

```bash
cd apps/web
npm install
npm run dev -- -p 3100
```

Then open:

- Web UI: http://localhost:3100
- API docs: http://localhost:8100/docs

Log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`.

## Importing data

In the dashboard, click **Ajouter des données** and upload a `.xlsx` workbook
matching the KPI template (one sheet per KPI, header text must match — column
order doesn't matter). The API validates the workbook first (structure,
types, cross-field checks) and only commits on confirmation, as one
all-or-nothing transaction. A seed/reference workbook is available at
`data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx`.

See `docs/` for the full KPI catalog, data contract, and import spec.

## Running tests

```bash
cd apps/api
source .venv/Scripts/activate
ruff check .
mypy .
pytest -q
```

```bash
cd apps/web
npm run lint
npm run typecheck
npx playwright test
```

## Project layout

```text
apps/api/kpi/       # KpiSpec registry, parser, validators, analytics, service, router
apps/api/alembic/   # migrations
apps/web/app/       # Next.js routes (dashboard, per-section, per-KPI detail, PDF print view)
apps/web/components/kpi/  # KPI card/panel/breakdown UI
data/imports/seed/  # reference workbook
docs/               # KPI catalog, data contract, product spec, import spec
```
