# Master implementation prompt — RSU KPI Dashboard

Work end-to-end in this repository.

## Objective

Transform `RSU_DASHBOARD_HUB` into a **single interactive application**:
**Dashboard de pilotage des processus du RSU**.

The only visible product is this dashboard. Remove every legacy dashboard, hub, admin/report/data-platform feature, route, endpoint, component and business model that is not necessary for this final KPI dashboard.

The dashboard must support the 22 KPI in `docs/KPI_CATALOG.md`, read the supplied workbook at:

`data/imports/seed/Donnees_synthetiques_kpi_VF.xlsx`

and support adding newer Excel data later without code changes.

## Required workflow

### Phase 1 — Inspect and plan
Before editing:
1. inspect the repository structure and dependencies;
2. read every handoff document;
3. inspect current RSU brand implementation (`tailwind.config.ts`, `globals.css`, `BrandMark`, sidebar, generic cards/tables/charts);
4. produce a concise `KEEP / MODIFY / DELETE / CREATE` plan;
5. identify migration risks.

Then proceed without waiting for another confirmation unless you encounter an actual ambiguity that blocks correctness.

### Phase 2 — Data foundation
Implement:
- multi-sheet Excel parser;
- schema normalization;
- validation;
- import preview;
- persistent import/upsert;
- import history/provenance;
- KPI analytics layer;
- typed FastAPI responses.

Use the contract in `docs/DATA_CONTRACT.md` and `docs/API_IMPORT_SPEC.md`.

### Phase 3 — Dashboard
Build one interactive dashboard with:
- global filters;
- overview;
- seven internal sections;
- all 22 KPIs;
- KPI-specific breakdowns;
- correct tooltips/units/no-data states;
- an internal “Ajouter des données” import flow.

Do not create separate dashboard products/pages.

### Phase 4 — Brand fidelity
Reuse the existing RSU design system exactly as a product constraint:
- current palette/tokens;
- Inter;
- BrandMark visual language;
- sidebar density and dimensions;
- border/shadow/radius language;
- RSU green for primary emphasis;
- red only for negative/alert semantics;
- neutral/paper surfaces;
- existing table/chart styling conventions.

Do not introduce a generic dashboard template, gradients, glassmorphism, oversized radii, a new color palette or another visual identity.

### Phase 5 — Remove legacy product
After the new path is working:
- remove the dashboard hub;
- remove `macro-national`;
- remove `programmes-sociaux-rescoring`;
- remove old reporting / FMS / ASD / AMO / budget business logic;
- remove unused admin/upload/report infrastructure;
- remove unused routes, types, docs, fixtures and tests;
- keep auth/database/storage infrastructure only if it is used by the final product.

Run global searches for legacy names and eliminate dead references.

### Phase 6 — Test and review
Run:
- backend unit/integration tests;
- Ruff/Mypy if configured and relevant;
- frontend typecheck;
- frontend build;
- Playwright smoke flow;
- app runtime;
- visual review at desktop and mobile widths.

Verify:
- seed workbook imports;
- all 22 KPI render;
- filters recalculate correctly;
- import preview rejects invalid workbooks;
- valid incremental import persists;
- duplicate import is idempotent;
- national percentile rules are respected;
- no old dashboard is reachable;
- no critical console errors.

## Final deliverable

The repository should look as if it had been designed from day one for one purpose:

> ingest RSU KPI data and interactively pilot the 22 RSU process KPIs.

Do not stop with a partial scaffold. Complete the working migration and report:
- files added/modified/deleted;
- architecture;
- tests run and results;
- any remaining explicit limitation.
