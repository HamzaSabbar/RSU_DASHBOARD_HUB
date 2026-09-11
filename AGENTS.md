# AGENTS.md — RSU KPI Dashboard

## Mission

Refactor this repository into **one single interactive RSU KPI dashboard** for the 22 process KPIs defined in `docs/KPI_CATALOG.md`.

There must be no dashboard hub, no second dashboard, and no legacy business workflow in the final product.

Read before coding:
- `docs/PRODUCT_SPEC.md`
- `docs/ARCHITECTURE_MIGRATION.md`
- `docs/DATA_CONTRACT.md`
- `docs/KPI_CATALOG.md`
- `docs/BRAND_UI_SPEC.md`
- `docs/API_IMPORT_SPEC.md`
- `docs/TEST_ACCEPTANCE.md`

## Non-negotiable rules

1. Preserve the existing RSU brand implementation. Do not redesign from scratch.
2. Reuse generic components only when they fit the new KPI product.
3. Delete legacy dashboards/features/components/endpoints after dependencies are removed.
4. `/` must open or redirect directly to the single KPI dashboard.
5. The application must ingest the multi-sheet `.xlsx` workbook and support future imports.
6. Persist imported data. New imports must survive server restarts.
7. Never average percentages. Aggregate ratios as `SUM(numerator) / SUM(denominator)`.
8. Never average medians/P75/P90.
9. For INS-02 and MAJ-01 national percentiles, use only the explicit national summary tables supplied by the workbook.
10. For weighted means (REC-01, REC-04, FSC-01 in the current synthetic perimeter), use the relevant volume as weight.
11. Validate before persistence. Invalid data must not silently enter KPI calculations.
12. Do not use `fillna(0)` when null and zero have different meanings.
13. Incremental imports must be idempotent and deduplicated by KPI natural keys.
14. The imported file is a data interface, not a hard-coded one-off fixture.
15. Keep runtime/imported data out of Git unless explicitly authorized.
16. Do not commit confidential source documents.

## Working method

Before destructive edits, produce a short `KEEP / MODIFY / DELETE / CREATE` plan based on actual repository dependency inspection.

Then:
1. implement data parser/validation/import persistence;
2. implement KPI analytics/API;
3. build the single dashboard;
4. migrate navigation/branding;
5. remove legacy functionality and dead code;
6. run backend tests;
7. run frontend typecheck/build;
8. run Playwright smoke tests;
9. run the app and visually review the key flows;
10. search the repository for legacy references and remove any unused remains.

Do not stop at code generation. Finish with an executable, tested application.
