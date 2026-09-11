"""DB <-> DataFrame bridge and response shaping for the KPI read API.

Fetches rows into pandas DataFrames (one query per table), then delegates all
statistical logic to the pure functions in `analytics.py`. Keeping DB access
here and math there is what lets `analytics.py` be unit tested without a
database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import cast

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kpi import analytics
from kpi.models import KpiGeography, KpiImport
from kpi.registry import (
    SECTIONS,
    AggregationStrategy,
    KpiSpec,
    SheetTableSpec,
    discover_kpis,
)

# All 18 KPIs shown on "Vue d'ensemble" (docs/PRODUCT_SPEC.md §7, overridden
# by explicit product decision: the overview must surface every KPI, not a
# compact pilot-signal subset).
OVERVIEW_CODES: tuple[str, ...] = (
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
)

GLOBAL_GEO_DIMENSIONS = {"period", "region", "province", "milieu"}


@dataclass
class KpiCard:
    code: str
    title: str
    section: str
    unit: str
    lower_is_better: bool
    value: float | None
    windows: dict[str, float | None]
    previous_value: float | None
    delta_abs: float | None
    delta_pct: float | None
    trend: list[dict[str, object]]
    available: bool
    unavailable_reason: str | None
    applied_filters: dict[str, object]
    ignored_filters: list[str]
    # This KPI's reporting cadence ("month"/"quarter"), stamped from
    # `spec.period_grain` so the dashboard's delta badge can say "vs mois
    # précédent" / "vs trimestre précédent" without threading `KpiMetadata`
    # through the overview page too.
    period_grain: str = "month"
    # Secondary counts that don't share `windows`'s unit (e.g. REC-06's
    # headline is a delay in days, but "en cours"/"clôturés" are raw counts)
    # -- populated only for KPIs with `spec.extra_measures`, empty otherwise.
    secondary_counts: dict[str, float | None] = field(default_factory=dict)
    # Precomputed here (not fetched again client-side on every page load) so
    # the dashboard doesn't fire one extra request per KPI panel just to
    # render its initially-selected "Ventiler par" dimension. The frontend
    # only calls GET /api/kpi/{code}?breakdown=... when the user switches to
    # a *different* dimension than this one.
    default_breakdown_dimension: str | None = None
    default_breakdown_items: list[dict[str, object]] | None = None


def _table_by_key(spec: KpiSpec, table_key: str) -> SheetTableSpec:
    return next(t for t in spec.tables if t.table_key == table_key)


def _main_table(spec: KpiSpec) -> SheetTableSpec:
    return _table_by_key(spec, "main")


def _national_table(spec: KpiSpec) -> SheetTableSpec:
    assert spec.percentile_table_index is not None
    return spec.tables[spec.percentile_table_index]


async def _fetch_table_df(session: AsyncSession, table_spec: SheetTableSpec) -> pd.DataFrame:
    model = table_spec.model
    fields = [c.field for c in table_spec.columns]
    stmt = select(*[getattr(model, f) for f in fields])
    rows = (await session.execute(stmt)).all()
    df = pd.DataFrame(rows, columns=fields)
    for col in table_spec.columns:
        if col.dtype in ("int", "float") and col.field in df.columns:
            df[col.field] = pd.to_numeric(df[col.field], errors="coerce")
    return df


def _filter_period_range(
    df: pd.DataFrame, start: date | None, end: date | None
) -> pd.DataFrame:
    if "period" not in df.columns:
        return df
    if start is not None:
        df = df[df["period"] >= start]
    if end is not None:
        df = df[df["period"] <= end]
    return df


async def _filtered_table_df(
    session: AsyncSession, spec: KpiSpec, table_key: str, filters: dict[str, object]
) -> pd.DataFrame:
    df = await _fetch_table_df(session, _table_by_key(spec, table_key))
    df = _filter_period_range(df, filters.get("period_start"), filters.get("period_end"))  # type: ignore[arg-type]
    dim_filters = {k: v for k, v in filters.items() if k not in ("period_start", "period_end")}
    return analytics.apply_filters(df, spec, dim_filters)


async def _filtered_main_df(
    session: AsyncSession, spec: KpiSpec, filters: dict[str, object]
) -> pd.DataFrame:
    return await _filtered_table_df(session, spec, "main", filters)


def _headline(spec: KpiSpec, values: dict[str, object]) -> float | None:
    if spec.aggregation_strategy == AggregationStrategy.RATIO:
        assert spec.ratio_windows is not None
        last_label = spec.ratio_windows[-1][0]
        return values.get(last_label)  # type: ignore[return-value]
    return values.get("value")  # type: ignore[return-value]


async def compute_kpi_card(
    session: AsyncSession, spec: KpiSpec, filters: dict[str, object]
) -> KpiCard:
    applied, ignored = analytics.applied_and_ignored_filters(spec, filters)

    if spec.aggregation_strategy == AggregationStrategy.PERCENTILE:
        return await _compute_percentile_card(session, spec, filters, applied, ignored)

    df = await _filtered_main_df(session, spec, filters)
    trend = analytics.trend_by_period(df, spec)
    current = trend[-1] if trend else {}
    previous = trend[-2] if len(trend) > 1 else {}
    value = _headline(spec, current)
    prev_value = _headline(spec, previous) if previous else None

    if spec.aggregation_strategy == AggregationStrategy.STOCK and current:
        d_abs = current.get("delta_abs")
        d_pct = current.get("delta_pct")
    else:
        d_abs, d_pct = analytics.delta(value, prev_value)

    extra_labels = {label for label, _, _ in spec.extra_measures}
    windows: dict[str, float | None] = {
        k: cast("float | None", v)
        for k, v in current.items()
        if k not in ("period", "delta_abs", "delta_pct") and k not in extra_labels
    }
    secondary_counts: dict[str, float | None] = {
        label: cast("float | None", current.get(label)) for label in extra_labels
    }
    return KpiCard(
        code=spec.code,
        title=spec.title,
        section=spec.section,
        unit=spec.unit,
        lower_is_better=spec.lower_is_better,
        value=value,
        windows=windows,
        previous_value=prev_value,
        delta_abs=d_abs,  # type: ignore[arg-type]
        delta_pct=d_pct,  # type: ignore[arg-type]
        trend=trend,
        available=True,
        unavailable_reason=None,
        applied_filters=applied,
        ignored_filters=ignored,
        period_grain=spec.period_grain,
        secondary_counts=secondary_counts,
    )


async def _compute_percentile_card(
    session: AsyncSession,
    spec: KpiSpec,
    filters: dict[str, object],
    applied: dict[str, object],
    ignored: list[str],
) -> KpiCard:
    assert spec.percentile_fields is not None
    non_period_dims = [k for k in applied if k != "period"]
    national_df = await _fetch_table_df(session, _national_table(spec))

    if national_df.empty:
        return KpiCard(
            code=spec.code,
            title=spec.title,
            section=spec.section,
            unit=spec.unit,
            lower_is_better=spec.lower_is_better,
            value=None,
            windows={},
            previous_value=None,
            delta_abs=None,
            delta_pct=None,
            trend=[],
            available=False,
            unavailable_reason="aucune donnée nationale importée",
            applied_filters=applied,
            ignored_filters=ignored,
            period_grain=spec.period_grain,
        )

    national_df = national_df.sort_values("period")
    periods: list[date] = national_df["period"].tolist()
    start, end = filters.get("period_start"), filters.get("period_end")
    eligible = [
        p
        for p in periods
        if (start is None or p >= start) and (end is None or p <= end)  # type: ignore[operator]
    ]
    if not eligible:
        eligible = periods

    trend: list[dict[str, object]] = []
    for p in eligible:
        point: dict[str, object] = {"period": p}
        point.update(
            analytics.national_percentile(national_df, period=p, fields=spec.percentile_fields)
            or {"median": None, "p75": None, "p90": None}
        )
        trend.append(point)

    available = not non_period_dims
    unavailable_reason: str | None = None
    values = trend[-1] if trend else None
    if non_period_dims:
        unavailable_reason = (
            "percentile national uniquement disponible sans filtre supplémentaire "
            f"(non supporté : {', '.join(non_period_dims)})"
        )
    elif values is None or values.get("median") is None:
        available = False
        unavailable_reason = "pas de valeur nationale publiée pour cette période"

    # Comparing the same national median at two consecutive periods is a
    # plain scalar comparison, not the forbidden "average percentiles across
    # subgroups" -- safe to delta exactly like every other strategy.
    current_median = cast("float | None", values.get("median")) if (available and values) else None
    previous = trend[-2] if len(trend) > 1 else None
    previous_median = cast("float | None", previous.get("median")) if previous else None
    d_abs, d_pct = analytics.delta(current_median, previous_median)

    return KpiCard(
        code=spec.code,
        title=spec.title,
        section=spec.section,
        unit=spec.unit,
        lower_is_better=spec.lower_is_better,
        value=current_median,
        windows={
            k: cast("float | None", v) for k, v in (values or {}).items() if k != "period"
        },
        previous_value=previous_median,
        delta_abs=d_abs,
        delta_pct=d_pct,
        trend=trend,
        available=available,
        unavailable_reason=unavailable_reason,
        applied_filters=applied,
        ignored_filters=ignored,
        period_grain=spec.period_grain,
    )


async def compute_breakdown(
    session: AsyncSession, spec: KpiSpec, filters: dict[str, object], dimension: str
) -> list[dict[str, object]]:
    """Groups the KPI's (filtered) population by `dimension`. Only dimensions
    declared in `spec.supported_breakdowns` are honored -- an unsupported or
    unknown dimension returns an empty list rather than guessing."""
    breakdown_spec = next(
        (b for b in spec.supported_breakdowns if b.dimension == dimension), None
    )
    if breakdown_spec is None:
        return []

    df = await _filtered_table_df(session, spec, breakdown_spec.table_key, filters)

    if spec.aggregation_strategy == AggregationStrategy.PERCENTILE:
        assert spec.percentile_fields is not None
        # The main table (not the national summary) carries a precomputed
        # median/P75/P90 per source row -- exactly what a source-grain
        # breakdown is allowed to display, per docs/KPI_CATALOG.md.
        return analytics.percentile_breakdown_by_source_grain(
            df, dimension=dimension, fields=_MAIN_TABLE_PERCENTILE_FIELDS
        )

    return analytics.breakdown_by(
        df,
        spec,
        dimension,
        ratio_windows_override=(
            (("value", breakdown_spec.numerator_field),)
            if breakdown_spec.numerator_field
            else None
        ),
        denominator_override=breakdown_spec.denominator_field,
    )


#: INS-02/MAJ-01's main table stores its own per-row median/P75/P90 under the
#: same generic column names regardless of KPI (see kpi/models.py).
_MAIN_TABLE_PERCENTILE_FIELDS: tuple[str, str, str] = ("mediane_jours", "p75_jours", "p90_jours")


async def compute_overview(
    session: AsyncSession, filters: dict[str, object]
) -> list[KpiCard]:
    registry = discover_kpis()
    return [await compute_kpi_card(session, registry[code], filters) for code in OVERVIEW_CODES]


#: `/api/kpi/filters` is called on every single dashboard navigation (see
#: apps/web/lib/kpi-api.ts `getKpiFilters`), but its result only changes when
#: an import is committed -- everything it reports (distinct filter values,
#: breakdown/measure metadata, period bounds) comes from `kpi_imports`-backed
#: tables. Recomputing it on every navigation meant a full-table pandas scan
#: per KPI (up to 25 tables) on the hot path of every page load, which is
#: what made e2e navigation timing unpredictable. Cached in-process and
#: invalidated by `invalidate_filter_options_cache()` right after a commit.
_filter_options_cache: dict[str, object] | None = None


def invalidate_filter_options_cache() -> None:
    global _filter_options_cache
    _filter_options_cache = None


async def get_filter_options(session: AsyncSession) -> dict[str, object]:
    global _filter_options_cache
    if _filter_options_cache is not None:
        return _filter_options_cache

    rows = (
        await session.execute(
            select(KpiGeography.region, KpiGeography.province, KpiGeography.milieu)
        )
    ).all()
    provinces_by_region: dict[str, set[str]] = {}
    milieux: set[str] = set()
    for region, province, milieu in rows:
        provinces_by_region.setdefault(region, set())
        if province:
            provinces_by_region[region].add(province)
        if milieu:
            milieux.add(milieu)

    per_kpi: dict[str, dict[str, object]] = {}
    registry = discover_kpis()
    for code, spec in registry.items():
        per_kpi[code] = await _kpi_metadata(session, spec)

    _filter_options_cache = {
        "regions": sorted(provinces_by_region.keys()),
        "provinces_by_region": {r: sorted(p) for r, p in provinces_by_region.items()},
        "milieux": sorted(milieux),
        "period": await _global_period_bounds(session),
        "sections": SECTIONS,
        "per_kpi": per_kpi,
    }
    return _filter_options_cache


async def _kpi_metadata(session: AsyncSession, spec: KpiSpec) -> dict[str, object]:
    """Per-KPI metadata for the frontend's "Ventiler par" selector and filter
    controls: every dimension is declared explicitly on the KpiSpec (never a
    fixed set imposed across all 18 KPIs) -- this just serializes it, plus
    the actual distinct values seen in the imported data for each filterable
    non-global dimension."""
    kpi_specific_filters = spec.supported_filters - GLOBAL_GEO_DIMENSIONS

    # Usually just the main table; INS-03's controlled_field/incoherence_type
    # values live only on its field-analysis table, so pull in any other
    # table a breakdown references too.
    table_keys = {"main", *(b.table_key for b in spec.supported_breakdowns)}
    values_by_dim: dict[str, list[str]] = {}
    for table_key in table_keys:
        try:
            table_spec = _table_by_key(spec, table_key)
        except StopIteration:
            continue
        df = await _fetch_table_df(session, table_spec)
        for dim in kpi_specific_filters:
            if dim in values_by_dim:
                continue
            if dim in df.columns:
                values_by_dim[dim] = sorted(str(v) for v in df[dim].dropna().unique())

    return {
        "filters": values_by_dim,
        "breakdowns": [b.dimension for b in spec.supported_breakdowns],
        "default_breakdown": spec.default_breakdown,
        "measures": list(spec.measures),
        "time_dimension": spec.time_dimension,
    }


async def _global_period_bounds(session: AsyncSession) -> dict[str, date | None]:
    mins: list[date] = []
    maxs: list[date] = []
    for spec in discover_kpis().values():
        period_col = getattr(_main_table(spec).model, "period")  # noqa: B009
        row = (await session.execute(select(func.min(period_col), func.max(period_col)))).first()
        if row and row[0] is not None:
            mins.append(row[0])
            maxs.append(row[1])
    return {"min": min(mins) if mins else None, "max": max(maxs) if maxs else None}


async def resolve_import_mode(session: AsyncSession, requested: str | None) -> str:
    """First-ever import must be a baseline (all 18 KPI sheets); later ones default
    to incremental (a subset is allowed) unless the caller explicitly overrides."""
    if requested is not None:
        return requested
    existing = await session.scalar(select(KpiImport.id).where(KpiImport.status == "committed").limit(1))
    return "incremental" if existing is not None else "baseline"


async def list_imports(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[KpiImport]:
    stmt = (
        select(KpiImport)
        .order_by(KpiImport.uploaded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())
