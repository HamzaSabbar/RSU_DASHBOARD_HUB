# CLAUDE.md — RSU KPI Dashboard

You are working on the RSU KPI dashboard refactor.

Your persistent product instructions are in:
- `AGENTS.md`
- `docs/PRODUCT_SPEC.md`
- `docs/ARCHITECTURE_MIGRATION.md`
- `docs/DATA_CONTRACT.md`
- `docs/KPI_CATALOG.md`
- `docs/BRAND_UI_SPEC.md`
- `docs/API_IMPORT_SPEC.md`
- `docs/TEST_ACCEPTANCE.md`

## Primary target

The final repository contains **one dashboard only**: the interactive dashboard for the 22 RSU process KPIs.

Do not preserve legacy product surfaces merely because they already exist. Preserve technical primitives and brand elements only when they remain useful.

## Before changing files

Inspect the repository and report:
- KEEP
- MODIFY
- DELETE
- CREATE

Do not perform broad deletion until you have searched references/dependencies.

## Statistical correctness

Treat `docs/KPI_CATALOG.md` as binding. In particular:
- ratios are ratios of sums;
- means may require weighting;
- percentiles cannot be reconstructed from subgroup percentiles;
- null is not zero;
- unsupported aggregations must be marked unavailable instead of fabricated.

## UI correctness

Treat the existing RSU Tailwind tokens, BrandMark, spacing, sidebar language, card/table conventions and `docs/BRAND_UI_SPEC.md` as binding. Do not apply a generic SaaS redesign.

## Completion

Run tests and the application. Verify import, filters, all 22 KPI, responsive behavior, no dead routes, no legacy visible surfaces, and no critical browser-console errors.
