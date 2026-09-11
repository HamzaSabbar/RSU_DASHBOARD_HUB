# Architecture & Migration Specification

## Target architecture

```text
Excel .xlsx imports
      ↓
FastAPI import endpoint
      ↓
parser + normalization + validation
      ↓
transactional upsert / provenance
      ↓
PostgreSQL
      ↓
analytics/service layer
      ↓
typed KPI API
      ↓
Next.js / React
      ↓
single RSU KPI dashboard
```

## Why persistence is required

The product must allow new data to be added from the UI and survive:
- server restart;
- redeploy;
- multiple user sessions.

Therefore, the Excel workbook is an **import interface**, not the only runtime database.

The existing project already has FastAPI/Pandas/OpenPyXL and database infrastructure. Reuse what is clean and useful.

## KEEP

Unless dependency inspection proves otherwise:
- Next.js / React / TypeScript
- Tailwind
- Recharts
- Lucide icons
- generic UI primitives
- `BrandMark` visual language
- generic KPI/card/table/chart/no-data components that remain useful
- FastAPI
- Pandas
- OpenPyXL
- Pydantic
- PostgreSQL
- SQLAlchemy / Alembic
- Playwright/test infrastructure

The final app runs locally (no Docker): a local PostgreSQL instance,
`uvicorn --reload` for the API, `next dev` for the web app.

## MODIFY

- root routing: `/` → dashboard
- `/dashboard`: becomes the actual KPI dashboard, not a hub
- sidebar: internal KPI family navigation + data import
- auth: keep only if genuinely required by the final application
- database models: replace legacy business tables with KPI/import models
- API routing: replace board-specific endpoints with KPI/import endpoints
- generic components: adapt to KPI-specific payloads and the preserved brand
- README and environment configuration

## DELETE after dependency verification

Frontend legacy surfaces:
- dashboard hub behavior
- `macro-national`
- `programmes-sociaux-rescoring`
- old reports/print pages
- old admin pages if not used by the final product
- legacy upload flows
- legacy product-specific components/types

Backend legacy surfaces:
- `boards/macro_national`
- `boards/programmes_sociaux_rescoring`
- board registry/auto-discovery if no longer useful for a single product
- old reports modules
- old data-platform modules if final import pipeline replaces them
- old FMS/ASD/AMO/budget analytics
- unused legacy DB models/migrations after a safe migration path

Repository:
- obsolete docs/fixtures/tests/env variables
- dead imports
- inaccessible legacy routes

## CREATE

Suggested backend:
```text
apps/api/kpi/
  __init__.py
  schemas.py
  parser.py
  validation.py
  importer.py
  analytics.py
  service.py
  router.py
```

Suggested frontend:
```text
apps/web/app/(app)/dashboard/page.tsx
apps/web/components/kpi/
  dashboard-shell.tsx
  dashboard-filters.tsx
  kpi-card.tsx
  kpi-chart.tsx
  kpi-table.tsx
  section-nav.tsx
  import-data-dialog.tsx
  import-preview.tsx
  no-data.tsx
```

Exact names may follow repository conventions.

## Database design guidance

Because the 22 sheets have heterogeneous schemas, prefer typed KPI storage.

Acceptable implementation:
- one table per KPI (or per closely related physical schema);
- import/provenance table;
- optional normalized geography/dimension reference tables.

Every KPI row should be traceable to:
- import id;
- source filename;
- imported timestamp;
- source period if available.

Do not force all KPI rows into a single EAV/JSON blob if that destroys type safety or query clarity.

## Migration safety

Do destructive cleanup only after:
1. new API works;
2. new dashboard works;
3. seed import works;
4. tests pass.

Use a migration branch. Search references before deleting files.

## Security / confidentiality

Real RSU data and confidential methodology documents must not be committed by default.

Add runtime import directories and raw uploaded files to `.gitignore`.

If raw source workbooks are retained for audit, store them in an authorized private persistent location, not in the public static web bundle.
