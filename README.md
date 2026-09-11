# RSU KPI Dashboard

Dashboard de pilotage des 18 KPI du RSU (Registre Social Unifié). Import d'un
classeur Excel multi-feuilles (un onglet "Légende" + un onglet par KPI),
persistance PostgreSQL, dashboard authentifié avec filtres, tendances,
ventilations et export PDF.

## Stack

- **Web**: Next.js 14 (App Router) + TypeScript + Tailwind + Recharts + NextAuth v4
- **API**: FastAPI + SQLAlchemy 2 + Alembic + Pandas/openpyxl
- **DB**: PostgreSQL 16

## Lancer le projet

Prérequis : PostgreSQL 16, Python 3.11+, Node 20+.

```bash
cp .env.example .env
# éditer .env : NEXTAUTH_SECRET (openssl rand -base64 32), ADMIN_EMAIL /
# ADMIN_PASSWORD, DATABASE_URL / DATABASE_URL_SYNC vers ton Postgres local.

createdb -U <user> rsu_dashboard   # une seule fois

# API
cd apps/api
python -m venv .venv && .venv/Scripts/activate   # source .venv/bin/activate sur macOS/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Web (autre terminal)
cd apps/web
npm install
npm run dev
```

- Web: http://localhost:3100
- API docs: http://localhost:8100/docs

Login avec `ADMIN_EMAIL` / `ADMIN_PASSWORD` (`.env`).

## Importer des données

Sidebar → **Ajouter des données** → sélectionner un `.xlsx` conforme à
`docs/DATA_CONTRACT.md`. Preview de validation avant confirmation, rien n'est
écrit en base tant que ce n'est pas confirmé. Premier import : les 22
feuilles. Imports suivants : un sous-ensemble suffit (upsert par clé
naturelle).

Fichier d'exemple (données synthétiques) :
`data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx`.

## API

- `GET /api/kpi/filters` — options de filtres globaux + par KPI
- `GET /api/kpi/overview` — les 18 KPI (Vue d'ensemble)
- `GET /api/kpi/sections/{section}` — tous les KPI d'une des 7 familles
- `GET /api/kpi/{code}` — détail d'un KPI, `?breakdown={dimension}`
- `POST /api/kpi/imports/validate` — validation, aucune écriture
- `POST /api/kpi/imports` — commit d'un import validé
- `GET /api/kpi/imports` — historique des imports

## Tests

```bash
# API (venv actif, dans apps/api)
pytest -q
ruff check .
mypy .

# Web
cd apps/web
npm run typecheck
npm run lint
npm run build
npx playwright test   # app démarrée sur PLAYWRIGHT_BASE_URL (défaut http://localhost:3100)
```

## Docs de référence

- [`docs/KPI_CATALOG.md`](docs/KPI_CATALOG.md) — les 18 KPI, formules, règles statistiques
- [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) — format du classeur, mapping colonnes, validations
- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — périmètre produit
- [`docs/API_IMPORT_SPEC.md`](docs/API_IMPORT_SPEC.md) — contrat API import
