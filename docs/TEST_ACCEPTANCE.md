# Test Plan & Acceptance Criteria

## Backend tests

### Parsing
- loads all 22 seed sheets;
- reads normal header row correctly;
- reads INS-02 national K:N;
- reads INS-03 global A:F and field H:O;
- reads MAJ-01 national N:Q;
- rejects missing required columns;
- rejects malformed numeric values where required;
- does not collapse null into zero.

### Validation
Test every rule from `DATA_CONTRACT.md`.

Must include:
- ACC 30 <= 90 <= denominator;
- INS 30 <= 60 <= 90 <= initiated;
- percentile ordering;
- MAJ-01 zero-finalized/null-percentile rule;
- NOT-02 delivered + not-delivered equality;
- numerator <= denominator checks.

### Analytics
- ratio-of-sums, not average-of-ratios;
- REC-01 weighted mean;
- REC-04 weighted mean;
- FSC-01 mean weighting;
- stock monthly delta;
- delta pct null when previous = 0;
- national INS-02 percentiles come from national summary;
- national MAJ-01 percentiles come from national summary;
- unsupported percentile aggregate returns unavailable/null with reason.

### Filtering
- date;
- region;
- province;
- milieu;
- KPI-specific filters;
- province options depend on selected region.

### Import
- valid seed preview;
- valid seed commit;
- same file reimport is idempotent;
- later file updates matching natural keys;
- invalid file makes zero DB mutations;
- partial incremental workbook behavior matches contract;
- checksum duplicate detection.

## Frontend tests

### Type/build
- `npm run typecheck`
- `npm run build`

### Playwright smoke
At minimum:
1. visit `/`;
2. lands on KPI dashboard;
3. seven KPI process families are reachable;
4. all 22 KPI codes/titles are discoverable;
5. change a global filter;
6. values/charts update;
7. open “Ajouter des données”;
8. validate a workbook;
9. preview result renders;
10. no critical console error.

If test environment permits:
11. commit valid import;
12. verify refreshed data.

## Visual review

Desktop widths:
- ~1440
- ~1024

Mobile:
- ~390

Check:
- sidebar/header brand fidelity;
- no overflow;
- filter usability;
- chart legibility;
- table readability;
- no generic-template redesign;
- all empty/error states styled consistently.

## Repository cleanup checks

Global search should not reveal active product references to:
- macro-national / macro_national
- programmes-sociaux-rescoring / programmes_sociaux_rescoring
- ReportDashboard
- ASD
- AMO
- FMS
- economieBudgetaire
- old board hub
- old report jobs

Exceptions:
- migration history if technically required and clearly inert;
- git history is not part of this check.

## Definition of done

The implementation is done only when:

1. `/` opens the single KPI dashboard.
2. No dashboard hub is visible or needed.
3. No legacy dashboard is accessible.
4. All 22 KPI are implemented.
5. Seed workbook imports successfully.
6. New workbook data can be previewed and persisted.
7. Imports survive restart/redeploy through persistent storage.
8. Duplicate imports do not duplicate KPI rows.
9. Global and specific filters work.
10. Ratio aggregation is statistically correct.
11. Weighted means are correct.
12. Percentiles are never incorrectly averaged.
13. Invalid data cannot silently enter calculations.
14. Brand identity is preserved.
15. Responsive behavior is acceptable.
16. Backend tests pass.
17. Frontend typecheck passes.
18. Frontend build passes.
19. Playwright smoke test passes.
20. No critical browser-console errors.
21. Dead legacy code/routes/docs/tests are removed.
22. README explains only the final KPI product.
