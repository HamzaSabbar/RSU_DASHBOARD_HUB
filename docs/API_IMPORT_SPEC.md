# API & Import Persistence Specification

## Suggested KPI API

Names may be adapted to project conventions, but keep the responsibilities.

### Read
- `GET /api/kpi/filters`
- `GET /api/kpi/overview`
- `GET /api/kpi/sections/{section}`
- `GET /api/kpi/{code}`

### Import
- `POST /api/kpi/imports/validate`
- `POST /api/kpi/imports`
- `GET /api/kpi/imports`

Optional only if useful:
- `GET /api/kpi/imports/{id}`

Do not expose legacy `/api/boards/*` once the final product no longer uses it.

## Filter query parameters

Common:
- `start_date`
- `end_date`
- `region`
- `province_prefecture`
- `milieu`

Specific parameters may include:
- `canal`
- `genre`
- `tranche_age`
- `type_mise_a_jour`
- `complexite`
- `motif_recours`
- `motif_reclamation`
- `source_administrative`
- `type_flux`
- `champ_controle`
- `type_incoherence`
- `type_courrier`
- `regle_suspicion`
- `type_fraude`

## Import validation endpoint

Input:
- multipart `.xlsx`

The workbook's non-data `Légende` sheet (see docs/DATA_CONTRACT.md) is
excluded entirely from `recognizedSheets`/`unknownSheets`/`missingSheets` —
it is never counted or flagged either way.

Output example shape:
```json
{
  "valid": true,
  "filename": "kpi_2026_06.xlsx",
  "recognizedSheets": 18,
  "missingSheets": [],
  "unknownSheets": [],
  "period": {"min": "2026-01-01", "max": "2026-06-30"},
  "rows": {
    "read": 4200,
    "new": 780,
    "updated": 0,
    "unchanged": 3420
  },
  "errors": [],
  "warnings": []
}
```

No DB mutation.

## Import commit endpoint

Must:
1. repeat/verify validation server-side;
2. use a DB transaction;
3. create import provenance record;
4. upsert KPI rows by natural keys;
5. commit only if everything succeeds;
6. invalidate/revalidate relevant dashboard caches;
7. return import summary.

## Import provenance

Store at least:
- import id
- original filename
- checksum/hash
- uploaded/imported timestamp
- status
- row count
- recognized sheets
- min/max period where derivable

Optional:
- user id if auth is retained

A byte-identical duplicate file should be detected.

## Upsert semantics

Default:
- same natural key + same values → unchanged
- same natural key + different measure values → update, newest confirmed import becomes authoritative
- new natural key → insert

Preview must make updates visible before confirmation.

## Transactionality

Never persist only some sheets from a failed full import.

For an explicitly incremental subset workbook, the submitted recognized sheets form the transaction boundary.

## Persistence

Use PostgreSQL in the final durable product unless an equally durable, already-deployed repository mechanism is demonstrably simpler.

Raw uploaded files:
- do not place in the web public folder;
- do not commit to Git;
- retain only if needed for audit and storage is authorized.

## Caching

Permitted:
- cache parsed/query results;
- invalidate on successful import.

Do not let cache become the only source of truth.

## Error behavior

Return structured validation errors with:
- sheet
- row if known
- column if known
- rule/message

The UI should render them without stack traces.

## Security

- accept `.xlsx` only;
- enforce file-size limit;
- do not execute macros;
- do not trust filenames as paths;
- sanitize/log safely;
- require normal application authorization if auth is retained.
