from __future__ import annotations

import dataclasses
from datetime import date

import pandas as pd

from kpi import analytics
from kpi.registry import AggregationStrategy, discover_kpis


def test_ratio_of_sums_is_not_average_of_row_ratios() -> None:
    # Row A: 1/100 = 1%; Row B: 100/100 = 100%. Average of ratios = 50.5%.
    # Ratio of sums = (1+100)/(100+100) = 50.5% too here by coincidence-avoidance,
    # so pick numbers where the two diverge clearly.
    df = pd.DataFrame({"num": [1, 9], "den": [10, 10]})
    # average of row ratios: (0.1 + 0.9) / 2 = 0.5
    # ratio of sums: (1+9) / (10+10) = 0.5 -- still equal; use skewed denominators instead.
    df = pd.DataFrame({"num": [1, 9], "den": [10, 1000]})
    # row ratios: 0.1 and 0.009 -> average = 0.0545
    # ratio of sums: 10 / 1010 = 0.0099...
    result = analytics.aggregate_ratio(
        df, ratio_windows=(("value", "num"),), denominator_field="den"
    )
    ratio_of_sums = result["value"]
    average_of_row_ratios = ((1 / 10) + (9 / 1000)) / 2
    assert ratio_of_sums is not None
    assert abs(ratio_of_sums - (10 / 1010)) < 1e-9
    assert abs(ratio_of_sums - average_of_row_ratios) > 0.01


def test_ratio_composite_denominator_sums_multiple_fields() -> None:
    df = pd.DataFrame({"num": [10, 20], "a": [50, 50], "b": [50, 50]})
    result = analytics.aggregate_ratio(
        df, ratio_windows=(("value", "num"),), denominator_field=("a", "b")
    )
    # num sum = 30, denom sum = 200
    value = result["value"]
    assert value is not None
    assert abs(value - (30 / 200)) < 1e-9


def test_weighted_mean_is_not_plain_average() -> None:
    # weight-heavy row should dominate.
    df = pd.DataFrame({"weight": [1000, 1], "value": [10.0, 100.0]})
    result = analytics.aggregate_weighted_mean(df, weight_field="weight", value_field="value")
    assert result is not None
    plain_average = (10.0 + 100.0) / 2
    weighted = (1000 * 10.0 + 1 * 100.0) / 1001
    assert abs(result - weighted) < 1e-6
    assert abs(result - plain_average) > 1


def test_stock_delta_pct_null_when_previous_is_zero() -> None:
    d_abs, d_pct = analytics.delta(10.0, 0.0)
    assert d_abs == 10.0
    assert d_pct is None


def test_stock_delta_none_when_either_side_missing() -> None:
    assert analytics.delta(None, 5.0) == (None, None)
    assert analytics.delta(5.0, None) == (None, None)


def test_national_percentile_only_reads_national_table_never_derives() -> None:
    national_df = pd.DataFrame(
        {
            "period": [date(2026, 1, 1), date(2026, 2, 1)],
            "median": [10.0, 11.0],
            "p75": [18.0, 19.0],
            "p90": [30.0, 32.0],
        }
    )
    result = analytics.national_percentile(
        national_df, period=date(2026, 1, 1), fields=("median", "p75", "p90")
    )
    assert result == {"median": 10.0, "p75": 18.0, "p90": 30.0}

    # unknown period -> None, never fabricated from nearby rows.
    assert (
        analytics.national_percentile(
            national_df, period=date(2026, 3, 1), fields=("median", "p75", "p90")
        )
        is None
    )


def test_apply_filters_drops_inapplicable_dimensions() -> None:
    # A synthetic spec (not a catalog lookup): no real KPI has `period` as its
    # only dimension anymore (the original REC-03 was retired, and REC-05
    # -- formerly REC-08 -- gained geo dims), so this decouples the test from
    # catalog composition entirely.
    spec = dataclasses.replace(
        discover_kpis()["ACC-01"], supported_filters=frozenset({"period"})
    )
    df = pd.DataFrame({"period": [date(2026, 1, 1)], "region": ["Casablanca-Settat"]})
    # "region" isn't a dimension of this spec, so this filter must be
    # silently dropped, not raise or empty the frame.
    filtered = analytics.apply_filters(df, spec, {"region": "Somewhere Else"})
    assert len(filtered) == 1


def test_applied_and_ignored_filters_split() -> None:
    spec = discover_kpis()["ACC-01"]
    applied, ignored = analytics.applied_and_ignored_filters(
        spec, {"region": "X", "channel": "Portail", "period_start": None}
    )
    assert "region" in applied
    assert "channel" in ignored  # ACC-01 has no "channel" dimension (it has age_band)


def test_trend_by_period_stock_computes_month_over_month_delta() -> None:
    spec = discover_kpis()["MAJ-02"]
    assert spec.aggregation_strategy == AggregationStrategy.STOCK
    df = pd.DataFrame(
        {
            "period": [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
            "maj_en_cours": [100, 150, 120],
        }
    )
    trend = analytics.trend_by_period(df, spec)
    assert trend[0]["delta_abs"] is None  # no previous period
    assert trend[1]["delta_abs"] == 50
    delta_pct = trend[1]["delta_pct"]
    assert isinstance(delta_pct, float)
    assert abs(delta_pct - 0.5) < 1e-9
    assert trend[2]["delta_abs"] == -30


def test_aggregate_latest_never_sums_across_periods() -> None:
    df = pd.DataFrame(
        {
            "period": [date(2026, 1, 1), date(2026, 2, 1), date(2026, 2, 1)],
            "reclamations_en_cours": [100, 40, 10],
        }
    )
    # Only the rows for the most recent period (Feb: 40 + 10) count -- January's
    # 100 must never be added in, or an open backlog would be double-counted.
    assert analytics.aggregate_latest(df, field="reclamations_en_cours") == 50.0


def test_rec04_extra_measures_sum_vs_latest_in_a_multi_period_breakdown() -> None:
    """The bug this guards against: a naive `sum()` for both "clôturés" (a
    flow) and "en cours" (a stock) would double-count "en cours" whenever a
    breakdown groups rows spanning more than one period -- e.g. a région
    breakdown over a Jan-Mar date range must show Mars's open backlog per
    région, not Jan+Feb+Mar added together."""
    spec = discover_kpis()["REC-04"]
    df = pd.DataFrame(
        {
            "period": [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)],
            "region": ["Casablanca-Settat"] * 3,
            "nb_reclamations_cloturees": [5, 6, 7],
            "delai_moyen_jours": [3.0, 4.0, 5.0],
            "reclamations_en_cours": [20, 25, 15],
        }
    )
    items = analytics.breakdown_by(df, spec, "region")
    assert len(items) == 1
    item = items[0]
    assert item["cloturés"] == 18  # 5 + 6 + 7: a flow, safe to sum
    assert item["en_cours"] == 15  # March's own value only, never 20+25+15


def test_not01_extra_measures_are_both_plain_sums() -> None:
    """OTP réussi / notification reçue are secondary counts, both "sum" mode
    (no stock/snapshot semantics here, unlike REC-04's "en cours") -- they
    must never be added together as a substitute for the union numerator."""
    spec = discover_kpis()["NOT-01"]
    df = pd.DataFrame(
        {
            "period": [date(2026, 1, 1), date(2026, 2, 1)],
            "chefs_avec_numero_enregistre": [1000, 1200],
            "chefs_avec_otp_reussi": [300, 350],
            "chefs_avec_notification_recue": [900, 950],
            "chefs_avec_activite_observee": [950, 1000],
        }
    )
    trend = analytics.trend_by_period(df, spec)
    assert trend[0]["otp_reussi"] == 300
    assert trend[0]["notification_recue"] == 900
    assert trend[1]["otp_reussi"] == 350
    assert trend[1]["notification_recue"] == 950
    # headline value comes from the union column, never OTP+notifications.
    assert trend[0]["value"] is not None


def test_cqd02_headline_is_total_and_breakdown_returns_all_three_windows() -> None:
    """"total" must be the last `ratio_windows` entry: `_headline()` reads
    `ratio_windows[-1]`. A région breakdown must return rouge/orange/total
    per région for free -- no bespoke breakdown code, just the generic
    multi-window ratio splat."""
    spec = discover_kpis()["CQD-02"]
    df = pd.DataFrame(
        {
            "period": [date(2026, 1, 1), date(2026, 1, 1)],
            "region": ["A", "B"],
            "menages_actifs": [1000, 2000],
            "menages_soupconnes_rouge": [30, 40],
            "menages_soupconnes_orange": [20, 60],
            "menages_distincts_soupconnes": [50, 100],
        }
    )
    trend = analytics.trend_by_period(df, spec)
    assert trend[0]["total"] == (50 + 100) / (1000 + 2000)
    assert trend[0]["rouge"] == (30 + 40) / (1000 + 2000)
    assert trend[0]["orange"] == (20 + 60) / (1000 + 2000)

    items = {item["key"]: item for item in analytics.breakdown_by(df, spec, "region")}
    assert items["A"]["rouge"] == 30 / 1000
    assert items["A"]["orange"] == 20 / 1000
    assert items["A"]["total"] == 50 / 1000
    assert items["B"]["total"] == 100 / 2000
