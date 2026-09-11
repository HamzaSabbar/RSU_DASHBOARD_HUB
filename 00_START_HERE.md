# RSU KPI Dashboard — Handoff Pack

## Goal

Transform the existing repository `awlers/RSU_DASHBOARD_HUB` into **one single interactive application** whose only product purpose is:

> Pilot and analyze the 22 RSU process KPIs.

The final product must:
- open directly on the KPI dashboard;
- contain no dashboard hub and no legacy dashboards;
- preserve the existing RSU brand identity and interaction patterns;
- ingest the provided multi-sheet Excel workbook;
- validate, persist and merge new KPI data without code changes;
- recalculate the dashboard after new imports;
- remain statistically correct when filters/aggregations are applied.

## Files in this handoff

- `AGENTS.md` — persistent instructions for Codex / coding agents.
- `CLAUDE.md` — persistent instructions for Claude Code.
- `MASTER_PROMPT.md` — initial implementation prompt.
- `docs/PRODUCT_SPEC.md` — product behavior and UX target.
- `docs/ARCHITECTURE_MIGRATION.md` — keep / modify / delete / create plan.
- `docs/DATA_CONTRACT.md` — Excel parsing, validation and import contract.
- `docs/KPI_CATALOG.md` — all 22 KPI formulas, dimensions and aggregation rules.
- `docs/BRAND_UI_SPEC.md` — RSU design system constraints to preserve.
- `docs/API_IMPORT_SPEC.md` — API + persistent import behavior.
- `docs/TEST_ACCEPTANCE.md` — test plan and definition of done.
- `data/imports/seed/Donnees_synthetiques_22_KPI_RSU_FINAL.xlsx` — seed workbook.

## How to use

1. Clone/open:
   `https://github.com/awlers/RSU_DASHBOARD_HUB.git`

2. Create a dedicated branch before destructive cleanup, for example:
   `refactor/kpi-dashboard`

3. Copy this handoff pack into the repository root:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `docs/*`
   - the seed Excel file under `data/imports/seed/`

4. **Do not commit confidential source documents or future real RSU data unless repository privacy and authorization have been confirmed.**
   The application should gitignore uploaded/imported runtime data.

5. Start Codex or Claude Code from the repository root.

6. Paste the content of `MASTER_PROMPT.md` as the first task.

7. Ask the agent to work end-to-end:
   inspect → plan → implement → migrate → delete dead legacy code → test → run → visually review.

## Important source-of-truth order

When instructions conflict, use this order:
1. `docs/KPI_CATALOG.md` and `docs/DATA_CONTRACT.md` for KPI/data correctness.
2. Existing active RSU brand implementation in the repo + `docs/BRAND_UI_SPEC.md` for UI.
3. `docs/PRODUCT_SPEC.md` for product scope.
4. `docs/ARCHITECTURE_MIGRATION.md` for cleanup strategy.

Do not invent missing business rules. Fail visibly or mark a metric unavailable when the available aggregated data do not support a statistically valid calculation.
