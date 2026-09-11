"""Asserts that every KPI's declared metadata (supported_filters,
supported_breakdowns, default_breakdown, measures, aggregation_strategy)
matches what docs/DATA_CONTRACT.md and docs/KPI_CATALOG.md actually specify
for its source sheet -- one explicit expectation per KPI, never inferred
from a fixed set imposed across all 18.

Each breakdown is asserted as an (dimension, table_key) pair rather than just
a dimension name, since INS-03 is the one KPI where a breakdown reads a
different physical table than its own main sheet (its
`controlled_field`/`incoherence_type` breakdowns live on the field-analysis
table, not the A:F global table the headline ratio is computed from).
"""

from __future__ import annotations

from kpi.registry import AggregationStrategy, discover_kpis

# code -> (supported_filters, supported_breakdowns as (dimension, table_key),
#          default_breakdown, measures, aggregation_strategy)
EXPECTED: dict[str, tuple[frozenset[str], frozenset[tuple[str, str]], str | None, tuple[str, ...], AggregationStrategy]] = {
    "ACC-01": (
        frozenset({"period", "region", "province", "milieu", "age_band"}),
        frozenset({("age_band", "main"), ("region", "main"), ("province", "main"), ("milieu", "main")}),
        "age_band",
        ("30j", "90j"),
        AggregationStrategy.RATIO,
    ),
    "INS-01": (
        frozenset({"period", "region", "province", "milieu", "channel"}),
        frozenset({("channel", "main"), ("region", "main"), ("province", "main"), ("milieu", "main")}),
        "channel",
        ("30j", "60j", "90j"),
        AggregationStrategy.RATIO,
    ),
    "INS-02": (
        frozenset({"period", "region", "province", "milieu", "channel"}),
        frozenset({("channel", "main"), ("region", "main"), ("province", "main"), ("milieu", "main")}),
        "channel",
        ("median", "p75", "p90"),
        AggregationStrategy.PERCENTILE,
    ),
    "INS-03": (
        frozenset(
            {"period", "region", "province", "milieu", "controlled_field", "incoherence_type"}
        ),
        frozenset(
            {
                ("controlled_field", "field"),
                ("incoherence_type", "field"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "controlled_field",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "FSC-01": (
        frozenset({"period", "administrative_source", "flow_type"}),
        frozenset({("administrative_source", "main"), ("flow_type", "main")}),
        "administrative_source",
        ("value",),
        AggregationStrategy.WEIGHTED_MEAN,
    ),
    "MAJ-01": (
        frozenset(
            {"period", "region", "province", "milieu", "channel", "update_type", "complexity"}
        ),
        frozenset(
            {
                ("update_type", "main"),
                ("complexity", "main"),
                ("channel", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "update_type",
        ("median", "p75", "p90"),
        AggregationStrategy.PERCENTILE,
    ),
    "MAJ-02": (
        frozenset({"period", "region", "province", "milieu", "channel", "update_type"}),
        frozenset(
            {
                ("update_type", "main"),
                ("channel", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "update_type",
        ("value",),
        AggregationStrategy.STOCK,
    ),
    "MAJ-03": (
        frozenset({"period", "region", "province", "milieu", "channel", "update_type"}),
        frozenset(
            {
                ("update_type", "main"),
                ("channel", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "update_type",
        ("value",),
        AggregationStrategy.STOCK,
    ),
    "MAJ-04": (
        frozenset({"period", "region", "province", "milieu"}),
        frozenset({("region", "main"), ("province", "main"), ("milieu", "main")}),
        "region",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "NOT-01": (
        frozenset({"period", "region", "province", "milieu", "gender", "age_band"}),
        frozenset(
            {
                ("gender", "main"),
                ("age_band", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "gender",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "NOT-02": (
        frozenset({"period", "region", "province", "milieu", "mail_type"}),
        frozenset(
            {("mail_type", "main"), ("region", "main"), ("province", "main"), ("milieu", "main")}
        ),
        "mail_type",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "REC-01": (
        frozenset({"period", "recourse_motive", "region", "province", "milieu"}),
        frozenset(
            {
                ("recourse_motive", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "recourse_motive",
        ("value",),
        AggregationStrategy.WEIGHTED_MEAN,
    ),
    "REC-02": (
        frozenset({"period", "recourse_motive", "region", "province"}),
        frozenset({("recourse_motive", "main"), ("region", "main"), ("province", "main")}),
        "recourse_motive",
        ("value",),
        AggregationStrategy.STOCK,
    ),
    "REC-03": (
        frozenset({"period", "recourse_motive", "region", "province", "milieu"}),
        frozenset(
            {
                ("recourse_motive", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "recourse_motive",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "REC-04": (
        frozenset({"period", "channel", "region", "province", "milieu"}),
        frozenset(
            {
                ("channel", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "channel",
        ("value",),
        AggregationStrategy.WEIGHTED_MEAN,
    ),
    "REC-05": (
        frozenset({"period", "region", "province", "milieu"}),
        frozenset({("region", "main"), ("province", "main"), ("milieu", "main")}),
        "region",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "CQD-01": (
        frozenset(
            {
                "period",
                "region",
                "province",
                "milieu",
                "suspicion_rule",
                "suspected_fraud_type",
            }
        ),
        frozenset(
            {
                ("suspicion_rule", "main"),
                ("suspected_fraud_type", "main"),
                ("region", "main"),
                ("province", "main"),
                ("milieu", "main"),
            }
        ),
        "suspicion_rule",
        ("value",),
        AggregationStrategy.RATIO,
    ),
    "CQD-02": (
        frozenset({"period", "region", "province", "milieu"}),
        frozenset({("region", "main"), ("province", "main"), ("milieu", "main")}),
        "region",
        ("rouge", "orange", "total"),
        AggregationStrategy.RATIO,
    ),
}


def test_expected_mapping_covers_all_18_kpis() -> None:
    assert set(EXPECTED) == set(discover_kpis())


def test_period_grain_is_month_except_ins03_quarterly() -> None:
    registry = discover_kpis()
    assert registry["INS-03"].period_grain == "quarter"
    assert all(
        spec.period_grain == "month" for code, spec in registry.items() if code != "INS-03"
    )


def test_every_kpi_exposes_exactly_its_expected_filters_and_breakdowns() -> None:
    registry = discover_kpis()
    for code, (filters, breakdowns, default, measures, strategy) in EXPECTED.items():
        spec = registry[code]

        assert spec.supported_filters == filters, (
            f"{code}: supported_filters {spec.supported_filters} != expected {filters}"
        )

        actual_breakdowns = frozenset((b.dimension, b.table_key) for b in spec.supported_breakdowns)
        assert actual_breakdowns == breakdowns, (
            f"{code}: supported_breakdowns {actual_breakdowns} != expected {breakdowns}"
        )

        assert spec.default_breakdown == default, (
            f"{code}: default_breakdown {spec.default_breakdown!r} != expected {default!r}"
        )

        assert spec.measures == measures, f"{code}: measures {spec.measures} != expected {measures}"

        assert spec.aggregation_strategy == strategy, (
            f"{code}: aggregation_strategy {spec.aggregation_strategy} != expected {strategy}"
        )

        assert spec.time_dimension == "period", f"{code}: time_dimension must be 'period'"

        # A KPI can never break down by its own time dimension -- that axis
        # is already the trend chart's job.
        assert spec.time_dimension not in {d for d, _ in actual_breakdowns}


def test_every_breakdown_dimension_is_also_a_declared_filter_or_field_table_dimension() -> None:
    """A breakdown dimension must be something the KPI actually declares an
    opinion about -- either a supported filter, or (INS-03 only) a dimension
    that lives on a secondary table referenced by supported_filters too."""
    registry = discover_kpis()
    for spec in registry.values():
        for breakdown in spec.supported_breakdowns:
            assert breakdown.dimension in spec.supported_filters, (
                f"{spec.code}: breakdown dimension {breakdown.dimension!r} is not in "
                f"supported_filters {spec.supported_filters}"
            )


def test_default_breakdown_is_always_a_supported_breakdown_or_none() -> None:
    registry = discover_kpis()
    for spec in registry.values():
        if spec.default_breakdown is None:
            assert spec.supported_breakdowns == ()
        else:
            assert spec.default_breakdown in {b.dimension for b in spec.supported_breakdowns}


def test_percentile_kpis_use_the_shared_main_table_percentile_field_names() -> None:
    """INS-02 and MAJ-01 both store their own per-row median/P75/P90 under the
    same generic column names (mediane_jours/p75_jours/p90_jours) -- this is
    what lets kpi/service.py's `_MAIN_TABLE_PERCENTILE_FIELDS` constant serve
    both KPIs' source-grain breakdowns without a per-KPI override."""
    registry = discover_kpis()
    for code in ("INS-02", "MAJ-01"):
        spec = registry[code]
        main_table = next(t for t in spec.tables if t.table_key == "main")
        field_names = {c.field for c in main_table.columns}
        assert {"mediane_jours", "p75_jours", "p90_jours"} <= field_names
