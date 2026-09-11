"""The KPI spec registry.

One `KpiSpec` per KPI code declares everything needed to parse its workbook
sheet(s), validate the rows, store them, and compute its metric — a single
source of truth consumed by `parser.py`, `validation.py`, `importer.py`,
`analytics.py`, and `router.py`. This mirrors the `boards/registry.py` idiom
already used in this repo, but as a static dict (not `pkgutil` discovery):
the product ships a fixed set of 18 KPIs, not pluggable boards.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from sqlalchemy.orm import DeclarativeBase

from kpi import validation as v


class AggregationStrategy(str, Enum):
    """Which generic analytics strategy computes this KPI's headline value
    and its breakdowns. Never KPI-specific code -- one of five shared
    implementations in `analytics.py`."""

    RATIO = "ratio"
    WEIGHTED_MEAN = "weighted_mean"
    PERCENTILE = "percentile"
    STOCK = "stock"
    RAW = "raw"


@dataclass(frozen=True)
class ColumnSpec:
    """Maps one workbook column to a normalized DataFrame field."""

    source_name: str
    field: str
    dtype: str = "str"  # "int" | "float" | "str" | "date" | "quarter"
    nullable: bool = False


@dataclass(frozen=True)
class SheetTableSpec:
    """One physical table read out of a KPI's sheet (most KPIs have one)."""

    table_key: str  # "main" | "national" | "field"
    sheet_name: str
    header_row: int  # 0-based, passed to pandas `header=`
    usecols: str  # excel column-letter range, e.g. "A:H"
    columns: tuple[ColumnSpec, ...]
    model: type[DeclarativeBase]
    natural_key: tuple[str, ...]
    validators: tuple[v.ValidationRule, ...] = ()


@dataclass(frozen=True)
class BreakdownSpec:
    """One dimension a KPI can be grouped ("ventilé") by.

    Almost always reads the same `main` table used for the headline value, in
    which case `numerator_field`/`denominator_field` are left as `None` and
    the KPI's own `ratio_windows`/`denominator_field` (etc.) apply unchanged.
    INS-03 is the one KPI where a breakdown (by `controlled_field` or
    `incoherence_type`) must read the sheet's separate field-analysis table
    instead, with its own numerator column (`nb_incoherents`) -- `table_key`
    and the field overrides exist for exactly that case.
    """

    dimension: str
    table_key: str = "main"
    numerator_field: str | None = None
    denominator_field: str | tuple[str, ...] | None = None


@dataclass(frozen=True)
class KpiSpec:
    code: str
    section: str
    title: str
    unit: str
    aggregation_strategy: AggregationStrategy
    tables: tuple[SheetTableSpec, ...]
    # Every dimension usable to *restrict the analytical population* via a
    # global or KPI-specific filter (docs/DATA_CONTRACT.md's per-KPI
    # dimension list). Distinct from `supported_breakdowns`: a filter narrows
    # which rows are summed; a breakdown groups the (already filtered) rows.
    supported_filters: frozenset[str]
    # Explicit, ordered allowlist of dimensions this KPI can be grouped by.
    # Never inferred from `supported_filters` -- some KPIs have dimensions
    # that only make sense as filters (or, for INS-03, a breakdown dimension
    # that lives on a different physical table entirely).
    supported_breakdowns: tuple[BreakdownSpec, ...] = ()
    default_breakdown: str | None = None
    # The primary time dimension's field name (every KPI table has exactly
    # one). Almost always "period" -- kept explicit per-KPI rather than
    # assumed, since it is never itself an entry in `supported_breakdowns`
    # (its own trend chart already covers that axis).
    time_dimension: str = "period"
    # This KPI's actual reporting cadence -- distinct from `time_dimension`
    # (which is only ever the column name "period"). Drives the dashboard's
    # delta-badge label ("vs mois précédent" / "vs trimestre précédent").
    # Explicit per-KPI rather than inferred, since nothing else on `KpiSpec`
    # reliably encodes it (INS-03's "quarter" `ColumnSpec.dtype` is a parser
    # hint, not queryable metadata).
    period_grain: Literal["month", "quarter"] = "month"
    # Labels of the measure/window keys this KPI exposes in card + breakdown
    # responses, e.g. ("30j", "60j", "90j") for INS-01, ("median", "p75",
    # "p90") for INS-02/MAJ-01, or ("value",) for everything single-valued.
    measures: tuple[str, ...] = ("value",)
    lower_is_better: bool = False
    # Secondary counts reported *alongside* the headline value/windows, kept
    # out of `windows` because they don't share its unit (e.g. REC-04's
    # headline is a delay in days, but "en cours"/"clôturés" are raw counts).
    # "sum": summed across whatever rows are in the current group (correct
    # for a flow, e.g. "clôturés"). "latest": summed only across the rows
    # sharing the most recent period in the group -- never accumulated across
    # periods (correct for a stock/snapshot, e.g. "en cours"; a naive "sum"
    # would double-count an open backlog across every month in a date-range
    # filter or a multi-period breakdown).
    extra_measures: tuple[tuple[str, str, Literal["sum", "latest"]], ...] = ()
    # aggregation_strategy-specific field names, all referring to columns on
    # tables[0] (or, for PERCENTILE, tables[percentile_table_index]).
    # RATIO: one or more (label, numerator_field) windows sharing one denominator
    # (ACC-01/INS-01 report 30j/60j/90j windows; most ratio KPIs have exactly one,
    # labelled "value"). A window's numerator, like denominator_field below,
    # may itself be a tuple of fields summed together (REC-05's denominator:
    # preinscriptions + demandes_maj; CQD-02's "total" window: rouge + orange,
    # derived rather than read from its own often-blank source column).
    ratio_windows: tuple[tuple[str, str | tuple[str, ...]], ...] | None = None
    denominator_field: str | tuple[str, ...] | None = None
    # WEIGHTED_MEAN: value_i weighted by weight_i.
    weight_field: str | None = None
    value_field: str | None = None
    # STOCK: current value + month-over-month delta.
    stock_field: str | None = None
    # PERCENTILE: read only from tables[percentile_table_index], keyed by period.
    percentile_table_index: int | None = None
    percentile_fields: tuple[str, str, str] | None = None  # (median, p75, p90)


SECTIONS: dict[str, str] = {
    "acces": "Accès",
    "inscription": "Inscription",
    "fiabilisation-sources": "Fiabilisation des sources",
    "maj-rescoring": "Mise à jour & rescoring",
    "notification": "Notification",
    "recours-reclamations": "Recours & réclamations",
    "controle-qualite": "Contrôle qualité",
}

SECTION_CODES: dict[str, tuple[str, ...]] = {
    "acces": ("ACC-01",),
    "inscription": ("INS-01", "INS-02", "INS-03"),
    "fiabilisation-sources": ("FSC-01",),
    "maj-rescoring": ("MAJ-01", "MAJ-02", "MAJ-03", "MAJ-04"),
    "notification": ("NOT-01", "NOT-02"),
    "recours-reclamations": (
        "REC-01",
        "REC-02",
        "REC-03",
        "REC-04",
        "REC-05",
    ),
    "controle-qualite": ("CQD-01", "CQD-02"),
}

# Global filter keys every dimension name below is drawn from.
GLOBAL_DIMENSIONS = frozenset({"period", "region", "province", "milieu"})

# Workbook sheets that are pure documentation (never a KPI's data), excluded
# entirely from recognized/unknown/missing sheet counts by `parser.py` --
# never silently downgraded to an "unknown sheet" warning.
IGNORED_SHEET_NAMES: frozenset[str] = frozenset({"Légende"})


_REGISTRY: dict[str, KpiSpec] = {}


def register(spec: KpiSpec) -> KpiSpec:
    _REGISTRY[spec.code] = spec
    return spec


def discover_kpis() -> dict[str, KpiSpec]:
    if not _REGISTRY:
        # Import triggers module-level `register()` calls for all 22 KPIs.
        from kpi import specs as _specs  # noqa: F401

    return dict(_REGISTRY)


def get_kpi(code: str) -> KpiSpec:
    registry = discover_kpis()
    try:
        return registry[code]
    except KeyError as exc:
        raise KeyError(f"unknown KPI code {code!r}") from exc


def kpis_in_section(section: str) -> Sequence[KpiSpec]:
    registry = discover_kpis()
    codes = SECTION_CODES.get(section, ())
    return [registry[c] for c in codes if c in registry]
