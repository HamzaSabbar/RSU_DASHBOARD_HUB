"""Parses a KPI workbook's sheets into normalized pandas DataFrames.

One generic `parse_table()` drives every sheet via its `SheetTableSpec`:
read with the declared `header_row`/`usecols`, rename source headers to
normalized field names, and coerce dtypes. Numeric/date cells that fail
coercion are reported as validation issues rather than silently becoming
null (`docs/DATA_CONTRACT.md`: "rejects malformed numeric values").
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from kpi.registry import IGNORED_SHEET_NAMES, KpiSpec, SheetTableSpec, discover_kpis
from kpi.validation import ValidationIssue

_QUARTER_MONTHS = {"T1": 1, "T2": 4, "T3": 7, "T4": 10}


def parse_quarter_label(label: str) -> date | None:
    """"T1 2026" -> date(2026, 1, 1); returns None if unparseable."""
    parts = str(label).strip().split()
    if len(parts) != 2:
        return None
    quarter, year = parts
    month = _QUARTER_MONTHS.get(quarter.upper())
    if month is None or not year.isdigit():
        return None
    return date(int(year), month, 1)


@dataclass
class SheetParseResult:
    table_key: str
    sheet_name: str
    df: pd.DataFrame
    issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class WorkbookParseResult:
    recognized_sheets: list[str]
    unknown_sheets: list[str]
    missing_sheets: list[str]
    tables: dict[str, dict[str, SheetParseResult]]


def _coerce_column(
    raw: pd.Series, *, dtype: str, sheet: str, field_name: str
) -> tuple[pd.Series, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    was_present = raw.notna()

    if dtype == "int":
        coerced = pd.to_numeric(raw, errors="coerce").round().astype("Int64")
    elif dtype == "float":
        coerced = pd.to_numeric(raw, errors="coerce").astype("Float64")
    elif dtype == "date":
        coerced = pd.to_datetime(raw, errors="coerce")
        # A date cell sometimes arrives as a bare serial number instead of a
        # real datetime -- e.g. a cell whose Excel number format was never
        # set to a date format (common after a paste-as-values or a script-
        # generated export). `pd.to_datetime` on a bare number defaults to
        # treating it as nanoseconds since 1970, silently collapsing every
        # such row to 1970-01-01 instead of raising. Detect those cells and
        # reinterpret them as Excel's own date serials (days since
        # 1899-12-30, Excel's actual epoch under the 1900 date system).
        is_bare_number = raw.map(
            lambda v: pd.notna(v) and not isinstance(v, str | datetime | date | pd.Timestamp)
        )
        if is_bare_number.any():
            serials = pd.to_numeric(raw[is_bare_number], errors="coerce")
            coerced.loc[is_bare_number] = pd.to_datetime(
                serials, unit="D", origin="1899-12-30"
            )
        coerced = coerced.dt.date
    elif dtype == "quarter":
        coerced = raw.map(lambda v: parse_quarter_label(v) if pd.notna(v) else None)
    else:  # "str"
        coerced = raw.astype("string").str.strip()
        return coerced, issues

    now_missing = was_present & pd.isna(coerced)
    for idx in raw[now_missing].index:
        issues.append(
            ValidationIssue(
                "error",
                sheet,
                int(idx) + 6,
                field_name,
                "invalid_value",
                f"valeur non convertible en {dtype} pour {field_name}: {raw.loc[idx]!r}",
            )
        )
    return coerced, issues


def parse_table(workbook: pd.ExcelFile, table_spec: SheetTableSpec) -> SheetParseResult:
    try:
        raw_df = pd.read_excel(
            workbook,
            sheet_name=table_spec.sheet_name,
            header=table_spec.header_row,
            usecols=table_spec.usecols,
        )
    except Exception as exc:  # noqa: BLE001 -- untrusted upload at a system
        # boundary: a malformed/narrower-than-expected sheet (e.g. fewer
        # columns than `usecols` spans) must surface as one clean validation
        # error, never crash the whole import request.
        return SheetParseResult(
            table_key=table_spec.table_key,
            sheet_name=table_spec.sheet_name,
            df=pd.DataFrame(),
            issues=[
                ValidationIssue(
                    "error",
                    table_spec.sheet_name,
                    None,
                    None,
                    "sheet_structure_invalid",
                    f"structure de la feuille illisible (colonnes {table_spec.usecols} attendues) : {exc}",
                )
            ],
        )
    rename_map = {c.source_name: c.field for c in table_spec.columns}
    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    missing_source_cols = [c for c in rename_map if c not in raw_df.columns]

    issues: list[ValidationIssue] = []
    for col in missing_source_cols:
        issues.append(
            ValidationIssue(
                "error",
                table_spec.sheet_name,
                None,
                rename_map[col],
                "missing_column",
                f"colonne source absente: {col!r}",
            )
        )

    df = raw_df.rename(columns=rename_map)
    # Drop fully-blank trailing rows (openpyxl sometimes over-reports max_row).
    known_fields = [c.field for c in table_spec.columns if c.field in df.columns]
    df = df[known_fields].dropna(how="all").reset_index(drop=True)

    for col_spec in table_spec.columns:
        if col_spec.field not in df.columns:
            continue
        coerced, col_issues = _coerce_column(
            df[col_spec.field],
            dtype=col_spec.dtype,
            sheet=table_spec.sheet_name,
            field_name=col_spec.field,
        )
        df[col_spec.field] = coerced
        issues.extend(col_issues)

    return SheetParseResult(
        table_key=table_spec.table_key, sheet_name=table_spec.sheet_name, df=df, issues=issues
    )


def parse_workbook(file_bytes: bytes, *, mode: str) -> WorkbookParseResult:
    """`mode`: "baseline" requires every KPI sheet present; "incremental" allows a subset."""
    registry: dict[str, KpiSpec] = discover_kpis()
    known_sheet_names = {spec.tables[0].sheet_name for spec in registry.values()}

    workbook = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    # Pure-documentation sheets (e.g. "Légende") are never a KPI's data and
    # must never surface as an "unknown sheet" warning -- excluded before any
    # of the recognized/unknown/missing set algebra below.
    present_sheets = set(workbook.sheet_names) - IGNORED_SHEET_NAMES

    recognized = sorted(present_sheets & known_sheet_names)
    unknown = sorted(present_sheets - known_sheet_names)
    missing = sorted(known_sheet_names - present_sheets) if mode == "baseline" else []

    tables: dict[str, dict[str, SheetParseResult]] = {}
    for code, spec in registry.items():
        sheet_name = spec.tables[0].sheet_name
        if sheet_name not in recognized:
            continue
        tables[code] = {}
        for table_spec in spec.tables:
            tables[code][table_spec.table_key] = parse_table(workbook, table_spec)

    return WorkbookParseResult(
        recognized_sheets=recognized,
        unknown_sheets=unknown,
        missing_sheets=missing,
        tables=tables,
    )
