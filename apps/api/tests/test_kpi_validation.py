from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from kpi.parser import parse_workbook
from kpi.registry import discover_kpis
from kpi.validation import (
    ConditionalNull,
    NonNegative,
    NumeratorLessEqualDenominator,
    Ordering,
    SumEquals,
    SumLessEqual,
    UniqueKey,
    run_validators,
)

SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "imports"
    / "seed"
    / "Donnees_synthetiques_kpi_VF.xlsx"
)


def test_seed_workbook_passes_every_validator() -> None:
    if not SEED_PATH.exists():
        pytest.skip(f"seed workbook not found at {SEED_PATH}")
    content = SEED_PATH.read_bytes()
    result = parse_workbook(content, mode="baseline")
    registry = discover_kpis()

    all_errors: list[object] = []
    for code, tables in result.tables.items():
        spec = registry[code]
        for table_spec in spec.tables:
            parsed = tables[table_spec.table_key]
            issues = run_validators(parsed.df, sheet=parsed.sheet_name, rules=table_spec.validators)
            all_errors.extend(i for i in issues if i.severity == "error")

    assert all_errors == []


def test_non_negative_flags_negative_values() -> None:
    df = pd.DataFrame({"a": [1, -2, 3]})
    issues = NonNegative(("a",)).check(df, sheet="X")
    assert len(issues) == 1
    assert issues[0].code == "negative_value"


def test_numerator_less_equal_denominator_flags_violation() -> None:
    df = pd.DataFrame({"num": [1, 5], "den": [2, 3]})
    issues = NumeratorLessEqualDenominator("num", "den").check(df, sheet="X")
    assert len(issues) == 1
    assert issues[0].row == 7  # second row -> index 1 -> row 1+6=7


def test_ordering_enforces_chain() -> None:
    df = pd.DataFrame({"a": [1, 10], "b": [2, 5], "c": [3, 20]})
    issues = Ordering(("a", "b", "c")).check(df, sheet="X")
    assert len(issues) == 1  # second row: b=5 > a=10 is False but c check: b<=c is fine; a<=b fails


def test_ordering_ignores_nulls() -> None:
    df = pd.DataFrame({"a": [1, None], "b": [2, None], "c": [3, None]})
    issues = Ordering(("a", "b", "c")).check(df, sheet="X")
    assert issues == []


def test_sum_equals_flags_mismatch() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": [1, 1], "total": [2, 4]})
    issues = SumEquals(("a", "b"), "total").check(df, sheet="X")
    assert len(issues) == 1


def test_conditional_null_flags_populated_value_when_condition_met() -> None:
    df = pd.DataFrame({"count": [0, 5], "pct": [1.5, 2.0]})
    issues = ConditionalNull("count", 0, "pct").check(df, sheet="X")
    assert len(issues) == 1
    assert issues[0].code == "should_be_null"


def test_unique_key_flags_duplicates() -> None:
    df = pd.DataFrame({"k1": ["a", "a", "b"], "k2": [1, 1, 2]})
    issues = UniqueKey(("k1", "k2")).check(df, sheet="X")
    assert len(issues) == 2  # both duplicate rows flagged


def test_cqd02_rouge_orange_must_sum_to_total() -> None:
    # CQD-02 shape: rouge/orange/total are three columns on the same row --
    # SumEquals enforces the mutually-exclusive-categories guarantee.
    df = pd.DataFrame(
        {
            "menages_soupconnes_rouge": [30, 30],
            "menages_soupconnes_orange": [20, 25],  # second row: 30+25 != 50
            "menages_distincts_soupconnes": [50, 50],
        }
    )
    issues = SumEquals(
        ("menages_soupconnes_rouge", "menages_soupconnes_orange"),
        "menages_distincts_soupconnes",
    ).check(df, sheet="X")
    assert len(issues) == 1
    assert issues[0].row == 7  # second row -> index 1 -> row 1+6=7


def test_sum_less_equal_flags_rouge_plus_orange_exceeding_active_households() -> None:
    df = pd.DataFrame(
        {
            "menages_soupconnes_rouge": [80, 30],
            "menages_soupconnes_orange": [40, 20],  # first row: 80+40 > 100
            "menages_actifs": [100, 100],
        }
    )
    issues = SumLessEqual(
        ("menages_soupconnes_rouge", "menages_soupconnes_orange"), "menages_actifs"
    ).check(df, sheet="X")
    assert len(issues) == 1
    assert issues[0].code == "sum_exceeds_total"


def test_sum_less_equal_ignores_rows_with_missing_values() -> None:
    df = pd.DataFrame({"a": [10, None], "b": [5, 3], "total": [12, None]})
    issues = SumLessEqual(("a", "b"), "total").check(df, sheet="X")
    assert len(issues) == 1  # only the fully-populated first row is checked (10+5 > 12)
