"""Generic aggregation strategies shared across all 18 KPIs.

Every function here is a pure pandas transform (no DB access), so ratio-of-
sums / weighted-mean / percentile-passthrough correctness can be unit tested
directly against small DataFrames.

Statistical rules enforced structurally (`docs/KPI_CATALOG.md`):
- ratios are always SUM(numerator) / SUM(denominator), never an average of
  row-level percentages (division happens once, after both sums are taken).
- weighted means are SUM(count_i * mean_i) / SUM(count_i).
- percentiles are never averaged or reconstructed from subgroups:
  * national trend/card figures come only from the national summary table
    passed in by the caller, and `national_percentile()` only ever accepts a
    period filter — there is no parameter through which a region/province/
    channel filter could reach it.
  * source-grain breakdowns of a percentile KPI (`percentile_breakdown_by_source_grain`)
    may pass a precomputed per-row median/P75/P90 straight through only when
    a breakdown group resolves to exactly one source row; a group spanning
    more than one row is marked unavailable rather than averaged.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from kpi.registry import AggregationStrategy, KpiSpec


def apply_filters(df: pd.DataFrame, spec: KpiSpec, filters: dict[str, object]) -> pd.DataFrame:
    """Drops any filter key the KPI doesn't have a dimension for, rather than
    letting it collapse the result to nothing or raise a KeyError. Filters
    *restrict the analytical population*; they are a distinct concept from a
    breakdown, which groups the already-restricted rows (see `breakdown_by`)."""
    out = df
    for key, value in filters.items():
        if value is None or key not in spec.supported_filters or key not in out.columns:
            continue
        if isinstance(value, list | tuple | set):
            out = out[out[key].isin(list(value))]
        else:
            out = out[out[key] == value]
    return out


def applied_and_ignored_filters(
    spec: KpiSpec, filters: dict[str, object]
) -> tuple[dict[str, object], list[str]]:
    present = {k: v for k, v in filters.items() if v is not None}
    applied = {k: v for k, v in present.items() if k in spec.supported_filters}
    ignored = [k for k in present if k not in spec.supported_filters]
    return applied, ignored


def _sum_or_none(series: pd.Series) -> float | None:
    if series.empty:
        return None
    total = series.sum(skipna=True)
    return float(total) if pd.notna(total) else None


def aggregate_ratio(
    df: pd.DataFrame,
    *,
    ratio_windows: tuple[tuple[str, str | tuple[str, ...]], ...],
    denominator_field: str | tuple[str, ...],
) -> dict[str, float | None]:
    denom = _sum_fields(df, denominator_field)
    result: dict[str, float | None] = {}
    for label, numerator_field in ratio_windows:
        num = _sum_fields(df, numerator_field)
        result[label] = (num / denom) if (num is not None and denom) else (0.0 if denom == 0 else None)
    return result


def _sum_fields(df: pd.DataFrame, field: str | tuple[str, ...]) -> float | None:
    """Sums one field, or several fields added together (e.g. REC-05's
    denominator `preinscriptions + demandes_maj`, or CQD-02's "total" window
    derived as `rouge + orange` rather than read from its own, often-blank,
    source column)."""
    fields = field if isinstance(field, tuple) else (field,)
    total = 0.0
    any_present = False
    for f in fields:
        if f not in df.columns:
            continue
        s = _sum_or_none(df[f])
        if s is not None:
            total += s
            any_present = True
    return total if any_present else None


def aggregate_weighted_mean(
    df: pd.DataFrame, *, weight_field: str, value_field: str
) -> float | None:
    if weight_field not in df.columns or value_field not in df.columns:
        return None
    mask = df[weight_field].notna() & df[value_field].notna()
    if not mask.any():
        return None
    weights = df.loc[mask, weight_field].astype(float)
    values = df.loc[mask, value_field].astype(float)
    total_weight = weights.sum()
    if total_weight == 0:
        return None
    return float((weights * values).sum() / total_weight)


def aggregate_stock(df: pd.DataFrame, *, stock_field: str) -> float | None:
    if stock_field not in df.columns:
        return None
    return _sum_or_none(df[stock_field])


def aggregate_latest(
    df: pd.DataFrame, *, field: str, period_field: str = "period"
) -> float | None:
    """Snapshot semantics for a secondary stock-style measure: sums only the
    rows sharing the most recent `period_field` value present in `df`, never
    accumulating across periods. `aggregate_stock` above is safe to call with
    a plain sum because `trend_by_period` only ever calls it on an
    already-single-period slice; `aggregate_group`'s `extra_measures` loop
    below has no such guarantee (a breakdown groups by dimension across the
    *whole* filtered, possibly multi-period, population), so a stock-style
    extra measure needs this instead of a plain sum."""
    if df.empty or field not in df.columns or period_field not in df.columns:
        return None
    latest = df[period_field].max()
    return _sum_or_none(df.loc[df[period_field] == latest, field])


def delta(current: float | None, previous: float | None) -> tuple[float | None, float | None]:
    if current is None or previous is None:
        return None, None
    delta_abs = current - previous
    delta_pct = None if previous == 0 else delta_abs / previous
    return delta_abs, delta_pct


def national_percentile(
    national_df: pd.DataFrame, *, period: date, fields: tuple[str, str, str]
) -> dict[str, float | None] | None:
    """Only accepts `period` — structurally cannot be asked for a subgroup."""
    if national_df.empty or "period" not in national_df.columns:
        return None
    row = national_df[national_df["period"] == period]
    if row.empty:
        return None
    median_f, p75_f, p90_f = fields
    r = row.iloc[0]
    return {
        "median": _clean_float(r.get(median_f)),
        "p75": _clean_float(r.get(p75_f)),
        "p90": _clean_float(r.get(p90_f)),
    }


def _clean_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return float(value)  # type: ignore[arg-type]


def aggregate_group(
    df: pd.DataFrame,
    spec: KpiSpec,
    *,
    ratio_windows_override: tuple[tuple[str, str], ...] | None = None,
    denominator_override: str | tuple[str, ...] | None = None,
) -> dict[str, float | None]:
    """Dispatches to the right strategy for a KPI's `aggregation_strategy`,
    given an already-filtered DataFrame slice (e.g. one period, or one
    breakdown key). The `*_override` params exist only for breakdowns that
    read a different physical table than the headline value does (INS-03's
    `controlled_field`/`incoherence_type`, whose numerator lives on the
    field-analysis table, not the main one) -- every other call site leaves
    them `None` and gets the KPI's own `ratio_windows`/`denominator_field`."""
    if spec.aggregation_strategy == AggregationStrategy.RATIO:
        windows = ratio_windows_override if ratio_windows_override is not None else spec.ratio_windows
        denom = denominator_override if denominator_override is not None else spec.denominator_field
        assert windows is not None and denom is not None
        result = aggregate_ratio(df, ratio_windows=windows, denominator_field=denom)
    elif spec.aggregation_strategy == AggregationStrategy.WEIGHTED_MEAN:
        assert spec.weight_field is not None and spec.value_field is not None
        result = {
            "value": aggregate_weighted_mean(
                df, weight_field=spec.weight_field, value_field=spec.value_field
            )
        }
    elif spec.aggregation_strategy == AggregationStrategy.STOCK:
        assert spec.stock_field is not None
        result = {"value": aggregate_stock(df, stock_field=spec.stock_field)}
    else:
        raise ValueError(f"aggregate_group does not handle {spec.aggregation_strategy}")

    for label, field, mode in spec.extra_measures:
        if field not in df.columns:
            result[label] = None
        elif mode == "sum":
            result[label] = _sum_or_none(df[field])
        else:
            result[label] = aggregate_latest(df, field=field)
    return result


def trend_by_period(df: pd.DataFrame, spec: KpiSpec) -> list[dict[str, object]]:
    """Chronological per-period aggregate (RATIO/WEIGHTED_MEAN/STOCK only —
    PERCENTILE trends come straight from the national table via `national_percentile`
    called once per period, since it must never be grouped-and-aggregated here)."""
    if "period" not in df.columns or df.empty:
        return []
    points: list[dict[str, object]] = []
    for period, group in df.groupby("period", sort=True):
        values = aggregate_group(group, spec)
        points.append({"period": period, **values})

    if spec.aggregation_strategy == AggregationStrategy.STOCK:
        prev_value: float | None = None
        for point in points:
            current = point.get("value")
            d_abs, d_pct = delta(current, prev_value)  # type: ignore[arg-type]
            point["delta_abs"] = d_abs
            point["delta_pct"] = d_pct
            prev_value = current  # type: ignore[assignment]
    return points


def breakdown_by(
    df: pd.DataFrame,
    spec: KpiSpec,
    dimension: str,
    *,
    ratio_windows_override: tuple[tuple[str, str], ...] | None = None,
    denominator_override: str | tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    """Groups the already-filtered population by `dimension` and aggregates
    each group with the KPI's usual strategy. Retains every measure the KPI
    exposes (e.g. INS-01's 30j/60j/90j all appear in each item), never just
    the first one."""
    if dimension not in df.columns or df.empty:
        return []
    items: list[dict[str, object]] = []
    for key, group in df.groupby(dimension, sort=True):
        values = aggregate_group(
            group,
            spec,
            ratio_windows_override=ratio_windows_override,
            denominator_override=denominator_override,
        )
        items.append({"key": key, **values})
    return items


def percentile_breakdown_by_source_grain(
    df: pd.DataFrame, *, dimension: str, fields: tuple[str, str, str]
) -> list[dict[str, object]]:
    """Groups a percentile KPI's main table by `dimension` without ever
    averaging medians/P75/P90 across rows: a group that resolves to exactly
    one source row passes its precomputed values through verbatim; a group
    spanning more than one row (i.e. the filters + this breakdown together
    do not isolate a single natural-key row) is marked unavailable."""
    if dimension not in df.columns or df.empty:
        return []
    median_f, p75_f, p90_f = fields
    items: list[dict[str, object]] = []
    for key, group in df.groupby(dimension, sort=True):
        if len(group) == 1:
            row = group.iloc[0]
            items.append(
                {
                    "key": key,
                    "median": _clean_float(row.get(median_f)),
                    "p75": _clean_float(row.get(p75_f)),
                    "p90": _clean_float(row.get(p90_f)),
                    "available": True,
                }
            )
        else:
            items.append(
                {"key": key, "median": None, "p75": None, "p90": None, "available": False}
            )
    return items
