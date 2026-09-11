"""Validate-then-commit import pipeline.

`validate_workbook()` never opens a write transaction — it is structurally
impossible for it to mutate the database, which is what `docs/API_IMPORT_SPEC.md`
requires of `POST /api/kpi/imports/validate`. `commit_workbook()` reuses the
exact same preview-building logic (so preview counts and commit counts can
never drift) and then performs the writes inside one transaction: insert the
`kpi_imports` provenance row, upsert every recognized sheet's rows by natural
key, upsert the derived `kpi_geography` index. A byte-identical checksum
short-circuits to the prior committed result for true idempotent dedupe.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from kpi.models import KpiGeography, KpiImport
from kpi.parser import WorkbookParseResult, parse_workbook
from kpi.registry import SheetTableSpec, discover_kpis
from kpi.validation import ValidationIssue, run_validators


@dataclass
class RowDiff:
    new: int = 0
    updated: int = 0
    unchanged: int = 0


@dataclass
class TablePreview:
    table_key: str
    sheet_name: str
    rows_read: int
    new: int
    updated: int
    unchanged: int
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)


@dataclass
class ImportPreview:
    valid: bool
    filename: str
    checksum: str
    mode: str
    recognized_sheets: list[str]
    missing_sheets: list[str]
    unknown_sheets: list[str]
    period_min: date | None
    period_max: date | None
    rows_read: int
    rows_new: int
    rows_updated: int
    rows_unchanged: int
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
    duplicate_of_import_id: str | None
    already_committed: bool
    per_kpi: dict[str, list[TablePreview]]


def _normalize_for_compare(value: object) -> object:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, Decimal):
        return round(float(value), 4)
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 4)
    return value


def _to_python(value: object) -> object:
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    return value


async def _diff_rows(
    session: AsyncSession, table_spec: SheetTableSpec, df: pd.DataFrame
) -> RowDiff:
    """Classifies each incoming row as new/updated/unchanged against the DB.

    Fetches the whole table once rather than building a `WHERE key IN (...)`
    over thousands of incoming natural-key tuples: for a sheet the size of
    MAJ-01 (~3840 rows x 7 key columns) that IN-list alone blew past tens of
    thousands of bind parameters and made validation take 20+ seconds. A
    plain full-table SELECT plus a Python dict lookup is both simpler and
    far faster for KPI-sheet-sized tables. `itertuples` is used instead of
    `iterrows` for the same reason -- the latter reconstructs a pandas
    Series per row, which is very slow at thousands of rows.
    """
    if df.empty:
        return RowDiff()

    model = table_spec.model
    key_cols = list(table_spec.natural_key)
    value_cols = [c.field for c in table_spec.columns if c.field not in key_cols]
    key_attrs = [getattr(model, k) for k in key_cols]
    value_attrs = [getattr(model, c) for c in value_cols]
    n_keys = len(key_cols)

    existing_rows = (await session.execute(select(*key_attrs, *value_attrs))).all()
    existing_by_key = {tuple(row[:n_keys]): tuple(row[n_keys:]) for row in existing_rows}

    diff = RowDiff()
    all_cols = [*key_cols, *value_cols]
    for record in df[all_cols].itertuples(index=False, name=None):
        key = record[:n_keys]
        incoming = tuple(_normalize_for_compare(v) for v in record[n_keys:])
        existing = existing_by_key.get(key)
        if existing is None:
            diff.new += 1
        elif tuple(_normalize_for_compare(v) for v in existing) == incoming:
            diff.unchanged += 1
        else:
            diff.updated += 1
    return diff


async def _build_preview(
    session: AsyncSession,
    *,
    parsed: WorkbookParseResult,
    filename: str,
    mode: str,
    checksum: str,
) -> ImportPreview:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    per_kpi: dict[str, list[TablePreview]] = {}
    rows_read = rows_new = rows_updated = rows_unchanged = 0
    period_min: date | None = None
    period_max: date | None = None

    for sheet in parsed.missing_sheets:
        errors.append(
            ValidationIssue(
                "error", sheet, None, None, "missing_sheet", f"feuille requise absente: {sheet}"
            )
        )
    for sheet in parsed.unknown_sheets:
        warnings.append(
            ValidationIssue(
                "warning",
                sheet,
                None,
                None,
                "unknown_sheet",
                f"feuille non reconnue ignorée: {sheet}",
            )
        )

    registry = discover_kpis()
    for code, tables in parsed.tables.items():
        spec = registry[code]
        table_previews: list[TablePreview] = []
        for table_spec in spec.tables:
            result = tables[table_spec.table_key]
            issues = list(result.issues)
            issues.extend(
                run_validators(result.df, sheet=result.sheet_name, rules=table_spec.validators)
            )
            table_errors = [i for i in issues if i.severity == "error"]
            table_warnings = [i for i in issues if i.severity == "warning"]
            errors.extend(table_errors)
            warnings.extend(table_warnings)

            diff = (
                await _diff_rows(session, table_spec, result.df)
                if not table_errors
                else RowDiff()
            )
            rows_read += len(result.df)
            rows_new += diff.new
            rows_updated += diff.updated
            rows_unchanged += diff.unchanged

            if "period" in result.df.columns and not result.df.empty:
                col = result.df["period"].dropna()
                if not col.empty:
                    col_min, col_max = col.min(), col.max()
                    period_min = col_min if period_min is None else min(period_min, col_min)
                    period_max = col_max if period_max is None else max(period_max, col_max)

            table_previews.append(
                TablePreview(
                    table_key=table_spec.table_key,
                    sheet_name=table_spec.sheet_name,
                    rows_read=len(result.df),
                    new=diff.new,
                    updated=diff.updated,
                    unchanged=diff.unchanged,
                    errors=table_errors,
                    warnings=table_warnings,
                )
            )
        per_kpi[code] = table_previews

    existing_import = await session.scalar(
        select(KpiImport).where(KpiImport.checksum == checksum, KpiImport.status == "committed")
    )

    return ImportPreview(
        valid=len(errors) == 0,
        filename=filename,
        checksum=checksum,
        mode=mode,
        recognized_sheets=parsed.recognized_sheets,
        missing_sheets=parsed.missing_sheets,
        unknown_sheets=parsed.unknown_sheets,
        period_min=period_min,
        period_max=period_max,
        rows_read=rows_read,
        rows_new=rows_new,
        rows_updated=rows_updated,
        rows_unchanged=rows_unchanged,
        errors=errors,
        warnings=warnings,
        duplicate_of_import_id=str(existing_import.id) if existing_import else None,
        already_committed=existing_import is not None,
        per_kpi=per_kpi,
    )


async def validate_workbook(
    session: AsyncSession, *, file_bytes: bytes, filename: str, mode: str
) -> ImportPreview:
    checksum = hashlib.sha256(file_bytes).hexdigest()
    parsed = parse_workbook(file_bytes, mode=mode)
    return await _build_preview(
        session, parsed=parsed, filename=filename, mode=mode, checksum=checksum
    )


def _collect_geography(
    table_spec: SheetTableSpec, df: pd.DataFrame, out: set[tuple[str, str | None, str | None]]
) -> None:
    fields = {c.field for c in table_spec.columns}
    if "region" not in fields:
        return
    has_province = "province" in fields
    has_milieu = "milieu" in fields
    for _, row in df.iterrows():
        region = row.get("region")
        if pd.isna(region):
            continue
        province = row.get("province") if has_province else None
        milieu = row.get("milieu") if has_milieu else None
        province = None if pd.isna(province) else str(province)
        milieu = None if pd.isna(milieu) else str(milieu)
        out.add((str(region), province, milieu))


async def _upsert_geography(
    session: AsyncSession, triples: set[tuple[str, str | None, str | None]]
) -> None:
    if not triples:
        return
    rows = [{"region": r, "province": p, "milieu": mi} for r, p, mi in triples]
    stmt = (
        pg_insert(KpiGeography)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["region", "province", "milieu"])
    )
    await session.execute(stmt)


# asyncpg rejects statements with more than 32767 bound parameters, so a KPI
# sheet with thousands of rows (e.g. MAJ-01's ~3840) cannot go into one INSERT.
# Batch conservatively regardless of column count.
_UPSERT_BATCH_SIZE = 500


async def _upsert_table(
    session: AsyncSession, table_spec: SheetTableSpec, df: pd.DataFrame, import_id: uuid.UUID
) -> None:
    if df.empty:
        return
    value_cols = [c.field for c in table_spec.columns if c.field not in table_spec.natural_key]
    all_cols = [*table_spec.natural_key, *value_cols]
    now = datetime.now(UTC)
    rows = []
    for source_row, record_values in zip(
        df.index, df[all_cols].itertuples(index=False, name=None), strict=True
    ):
        record = dict(zip(all_cols, (_to_python(v) for v in record_values), strict=True))
        record["first_seen_import_id"] = import_id
        record["last_import_id"] = import_id
        record["source_row"] = int(source_row) + 6
        record["updated_at"] = now
        rows.append(record)

    update_cols = (*value_cols, "last_import_id", "source_row", "updated_at")
    for start in range(0, len(rows), _UPSERT_BATCH_SIZE):
        batch = rows[start : start + _UPSERT_BATCH_SIZE]
        stmt = pg_insert(table_spec.model).values(batch)
        update_set = {f: getattr(stmt.excluded, f) for f in update_cols}
        stmt = stmt.on_conflict_do_update(
            index_elements=list(table_spec.natural_key), set_=update_set
        )
        await session.execute(stmt)


async def commit_workbook(
    session: AsyncSession,
    *,
    file_bytes: bytes,
    filename: str,
    mode: str,
    uploaded_by: uuid.UUID | None,
) -> ImportPreview:
    checksum = hashlib.sha256(file_bytes).hexdigest()
    parsed = parse_workbook(file_bytes, mode=mode)
    preview = await _build_preview(
        session, parsed=parsed, filename=filename, mode=mode, checksum=checksum
    )

    if preview.already_committed or not preview.valid:
        # Duplicate bytes -> idempotent no-op. Invalid -> caller (router) turns this
        # into a 422; either way, nothing below runs, so nothing is ever mutated.
        return preview

    import_row = KpiImport(
        filename=filename,
        checksum=checksum,
        uploaded_by=uploaded_by,
        mode=mode,
        status="committed",
        recognized_sheets=preview.recognized_sheets,
        missing_sheets=preview.missing_sheets,
        unknown_sheets=preview.unknown_sheets,
        row_counts={
            code: {
                "new": sum(t.new for t in tables),
                "updated": sum(t.updated for t in tables),
                "unchanged": sum(t.unchanged for t in tables),
            }
            for code, tables in preview.per_kpi.items()
        },
        period_min=preview.period_min,
        period_max=preview.period_max,
        committed_at=datetime.now(UTC),
    )
    session.add(import_row)
    await session.flush()

    registry = discover_kpis()
    geography: set[tuple[str, str | None, str | None]] = set()
    for code, tables in parsed.tables.items():
        spec = registry[code]
        for table_spec in spec.tables:
            result = tables[table_spec.table_key]
            await _upsert_table(session, table_spec, result.df, import_row.id)
            _collect_geography(table_spec, result.df, geography)

    await _upsert_geography(session, geography)
    await session.commit()
    return preview
