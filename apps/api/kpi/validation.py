"""Declarative, composable validation rules for parsed KPI sheet rows.

Each rule is a small object that inspects a pandas DataFrame (already parsed
and column-renamed by `parser.py`) and yields `ValidationIssue`s. The logic
for each rule lives here exactly once; each KPI's `SheetTableSpec.validators`
tuple just wires rule instances against that KPI's real column names, so 18
different sheet shapes stay expressible without 18 imperative validation
functions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "error" | "warning"
    sheet: str
    row: int | None
    column: str | None
    code: str
    message: str


class ValidationRule(Protocol):
    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]: ...


def _row_number(df: pd.DataFrame, idx: int) -> int:
    """1-based row number as it appears in the source workbook (header row + idx)."""
    return int(idx) + 6  # data starts at sheet row 6 (row1-4 metadata, row5 header)


@dataclass(frozen=True)
class RequiredColumns:
    columns: tuple[str, ...]

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for col in self.columns:
            if col not in df.columns:
                issues.append(
                    ValidationIssue(
                        "error", sheet, None, col, "missing_column", f"colonne requise absente: {col}"
                    )
                )
        return issues


@dataclass(frozen=True)
class NonNegative:
    columns: tuple[str, ...]

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for col in self.columns:
            if col not in df.columns:
                continue
            bad = df[df[col].notna() & (df[col] < 0)]
            for idx in bad.index:
                issues.append(
                    ValidationIssue(
                        "error",
                        sheet,
                        _row_number(df, idx),
                        col,
                        "negative_value",
                        f"{col} doit être >= 0",
                    )
                )
        return issues


@dataclass(frozen=True)
class NumeratorLessEqualDenominator:
    numerator: str
    denominator: str

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        if self.numerator not in df.columns or self.denominator not in df.columns:
            return []
        mask = (
            df[self.numerator].notna()
            & df[self.denominator].notna()
            & (df[self.numerator] > df[self.denominator])
        )
        return [
            ValidationIssue(
                "error",
                sheet,
                _row_number(df, idx),
                self.numerator,
                "numerator_gt_denominator",
                f"{self.numerator} doit être <= {self.denominator}",
            )
            for idx in df[mask].index
        ]


@dataclass(frozen=True)
class Ordering:
    """Enforces a <= b <= ... across a chain of columns, only where populated."""

    columns: tuple[str, ...]

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        present = [c for c in self.columns if c in df.columns]
        issues: list[ValidationIssue] = []
        for a, b in zip(present, present[1:], strict=False):
            mask = df[a].notna() & df[b].notna() & (df[a] > df[b])
            for idx in df[mask].index:
                issues.append(
                    ValidationIssue(
                        "error",
                        sheet,
                        _row_number(df, idx),
                        b,
                        "ordering_violation",
                        f"{a} doit être <= {b}",
                    )
                )
        return issues


@dataclass(frozen=True)
class SumEquals:
    """cols summed must equal `total`, only where all participating cells are populated."""

    columns: tuple[str, ...]
    total: str

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        cols = [c for c in self.columns if c in df.columns]
        if not cols or self.total not in df.columns:
            return []
        all_present = df[[*cols, self.total]].notna().all(axis=1)
        computed = df[cols].sum(axis=1)
        mismatch = all_present & (computed != df[self.total])
        return [
            ValidationIssue(
                "error",
                sheet,
                _row_number(df, idx),
                self.total,
                "sum_mismatch",
                f"{' + '.join(cols)} doit être égal à {self.total}",
            )
            for idx in df[mismatch].index
        ]


@dataclass(frozen=True)
class SumLessEqual:
    """cols summed must be <= `total`, only where all participating cells are populated."""

    columns: tuple[str, ...]
    total: str

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        cols = [c for c in self.columns if c in df.columns]
        if not cols or self.total not in df.columns:
            return []
        all_present = df[[*cols, self.total]].notna().all(axis=1)
        computed = df[cols].sum(axis=1)
        mismatch = all_present & (computed > df[self.total])
        return [
            ValidationIssue(
                "error",
                sheet,
                _row_number(df, idx),
                self.total,
                "sum_exceeds_total",
                f"{' + '.join(cols)} doit être <= {self.total}",
            )
            for idx in df[mismatch].index
        ]


@dataclass(frozen=True)
class ConditionalNull:
    """When `condition_column == condition_value`, `target_column` must be null."""

    condition_column: str
    condition_value: object
    target_column: str

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        if self.condition_column not in df.columns or self.target_column not in df.columns:
            return []
        mask = (df[self.condition_column] == self.condition_value) & df[self.target_column].notna()
        return [
            ValidationIssue(
                "error",
                sheet,
                _row_number(df, idx),
                self.target_column,
                "should_be_null",
                f"{self.target_column} doit être vide quand {self.condition_column} = {self.condition_value}",
            )
            for idx in df[mask].index
        ]


@dataclass(frozen=True)
class UniqueKey:
    columns: tuple[str, ...]

    def check(self, df: pd.DataFrame, *, sheet: str) -> list[ValidationIssue]:
        cols = [c for c in self.columns if c in df.columns]
        if len(cols) != len(self.columns):
            return []
        dupes = df[df.duplicated(subset=cols, keep=False)]
        return [
            ValidationIssue(
                "error",
                sheet,
                _row_number(df, idx),
                ",".join(cols),
                "duplicate_natural_key",
                "clé naturelle dupliquée dans cet import",
            )
            for idx in dupes.index
        ]


def run_validators(
    df: pd.DataFrame, *, sheet: str, rules: Sequence[ValidationRule]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for rule in rules:
        issues.extend(rule.check(df, sheet=sheet))
    return issues
