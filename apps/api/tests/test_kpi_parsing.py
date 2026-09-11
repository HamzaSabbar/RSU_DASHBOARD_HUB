from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from kpi.parser import _coerce_column, parse_quarter_label, parse_workbook
from kpi.registry import IGNORED_SHEET_NAMES, discover_kpis

SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "imports"
    / "seed"
    / "Donnees_synthetiques_kpi_VF.xlsx"
)


@pytest.fixture(scope="module")
def seed_bytes() -> bytes:
    if not SEED_PATH.exists():
        pytest.skip(f"seed workbook not found at {SEED_PATH}")
    return SEED_PATH.read_bytes()


def test_all_18_kpi_registered() -> None:
    registry = discover_kpis()
    assert len(registry) == 18
    expected = {
        "ACC-01",
        "INS-01",
        "INS-02",
        "INS-03",
        "FSC-01",
        "MAJ-01",
        "MAJ-02",
        "MAJ-03",
        "MAJ-04",
        "NOT-01",
        "NOT-02",
        "REC-01",
        "REC-02",
        "REC-03",
        "REC-04",
        "REC-05",
        "CQD-01",
        "CQD-02",
    }
    assert set(registry) == expected


def test_baseline_parse_recognizes_all_sheets(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="baseline")
    assert len(result.recognized_sheets) == 18
    assert result.missing_sheets == []
    assert result.unknown_sheets == []


def test_legend_sheet_is_excluded_from_counts(seed_bytes: bytes) -> None:
    workbook = pd.ExcelFile(io.BytesIO(seed_bytes), engine="openpyxl")
    assert set(IGNORED_SHEET_NAMES) & set(workbook.sheet_names) == IGNORED_SHEET_NAMES

    result = parse_workbook(seed_bytes, mode="baseline")
    for name in IGNORED_SHEET_NAMES:
        assert name not in result.recognized_sheets
        assert name not in result.unknown_sheets
        assert name not in result.missing_sheets


def test_no_coercion_issues_on_seed_workbook(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="baseline")
    for code, tables in result.tables.items():
        for table_key, parsed in tables.items():
            assert parsed.issues == [], f"{code}/{table_key}: {parsed.issues}"


def test_ins02_has_main_and_national_tables(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="baseline")
    tables = result.tables["INS-02"]
    assert set(tables) == {"main", "national"}
    assert list(tables["main"].df.columns) == [
        "period",
        "region",
        "province",
        "milieu",
        "channel",
        "dossiers_finalises",
        "mediane_jours",
        "p75_jours",
        "p90_jours",
    ]
    assert list(tables["national"].df.columns) == [
        "period",
        "mediane_nationale",
        "p75_national",
        "p90_national",
    ]
    assert not tables["main"].df.empty
    assert not tables["national"].df.empty


def test_maj01_has_main_and_national_tables(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="baseline")
    tables = result.tables["MAJ-01"]
    assert set(tables) == {"main", "national"}
    assert not tables["main"].df.empty
    assert not tables["national"].df.empty


def test_ins03_has_global_and_field_tables(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="baseline")
    tables = result.tables["INS-03"]
    assert set(tables) == {"main", "field"}
    assert list(tables["main"].df.columns) == [
        "period",
        "region",
        "province",
        "milieu",
        "personnes_avec_incoherence",
        "personnes_comparees",
    ]
    assert "controlled_field" in tables["field"].df.columns
    assert "incoherence_type" in tables["field"].df.columns
    assert not tables["field"].df.empty


def test_incremental_mode_allows_missing_sheets(seed_bytes: bytes) -> None:
    result = parse_workbook(seed_bytes, mode="incremental")
    assert result.missing_sheets == []  # seed has all 18; contract just doesn't *require* it


def test_parse_quarter_label() -> None:
    from datetime import date

    assert parse_quarter_label("T1 2026") == date(2026, 1, 1)
    assert parse_quarter_label("T2 2026") == date(2026, 4, 1)
    assert parse_quarter_label("T3 2026") == date(2026, 7, 1)
    assert parse_quarter_label("T4 2026") == date(2026, 10, 1)
    assert parse_quarter_label("garbage") is None


def test_coerce_date_column_handles_bare_excel_serial_numbers() -> None:
    """A date cell whose Excel number format was never set to a date format
    (e.g. after a paste-as-values, or a script-generated export) arrives as a
    bare serial number instead of a real datetime. `pd.to_datetime` on a bare
    number otherwise defaults to nanoseconds-since-1970, silently collapsing
    every such row to 1970-01-01 -- must instead be read as an Excel date
    serial (days since 1899-12-30)."""
    from datetime import date as date_cls
    from datetime import datetime

    raw = pd.Series([datetime(2026, 1, 1), 46023, 46054, None])
    coerced, issues = _coerce_column(raw, dtype="date", sheet="X", field_name="period")
    assert issues == []
    values = coerced.tolist()
    assert values[:3] == [
        date_cls(2026, 1, 1),
        date_cls(2026, 1, 1),
        date_cls(2026, 2, 1),
    ]
    assert pd.isna(values[3])
