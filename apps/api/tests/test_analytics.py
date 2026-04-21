from __future__ import annotations

from boards.macro_national import analytics, parser


def test_parser_detects_inscriptions_rnp_from_filename(inscriptions_xlsx_bytes: bytes) -> None:
    kind = parser.detect_file_kind("stat_nouveaux_inscrits_rnp.xlsx", inscriptions_xlsx_bytes)
    assert kind is not None
    assert kind.value == "inscriptions_rnp"


def test_parser_tidies_two_row_header(inscriptions_xlsx_bytes: bytes) -> None:
    df = parser.parse_inscriptions_rnp(inscriptions_xlsx_bytes)
    assert set(df.columns) == {"province", "month", "value"}
    assert set(df["province"].unique()) == {"Casablanca", "Rabat", "Tanger"}
    assert set(df["month"].unique()) == {"2025-01", "2025-02", "2025-03", "2025-04"}
    assert df.shape[0] == 12


def test_kpis_sum_and_last_month_pct(inscriptions_xlsx_bytes: bytes) -> None:
    df = parser.parse_inscriptions_rnp(inscriptions_xlsx_bytes)
    k = analytics.compute_inscriptions_kpis(df)
    # last month total: 2000 + 1300 + 500 = 3800, prev: 1800 + 1100 + 400 = 3300
    assert k.new_menages_last_month == 3800
    assert k.new_menages_last_month_pct_change is not None
    assert round(k.new_menages_last_month_pct_change, 2) == round(((3800 - 3300) / 3300) * 100, 2)
    # total: 12150
    assert k.total_menages == 1200+1500+1800+2000 + 800+900+1100+1300 + 300+350+400+500


def test_monthly_evolution_is_chronological_with_deltas(inscriptions_xlsx_bytes: bytes) -> None:
    df = parser.parse_inscriptions_rnp(inscriptions_xlsx_bytes)
    points = analytics.compute_monthly_evolution(df)
    months = [p.month for p in points]
    assert months == sorted(months)
    assert points[0].delta is None
    for prev, curr in zip(points, points[1:]):
        assert curr.delta == curr.value - prev.value


def test_top_provinces_orders_by_total_desc(inscriptions_xlsx_bytes: bytes) -> None:
    df = parser.parse_inscriptions_rnp(inscriptions_xlsx_bytes)
    top = analytics.compute_top_provinces(df, k=3)
    assert [p.province for p in top] == ["Casablanca", "Rabat", "Tanger"]
    assert [p.value for p in top] == [6500, 4100, 1550]


def test_empty_dataframe_returns_zeroed_kpis() -> None:
    import pandas as pd
    empty = pd.DataFrame(columns=["province", "month", "value"])
    k = analytics.compute_inscriptions_kpis(empty)
    assert k.total_menages == 0
    assert k.total_personnes == 0
    assert k.new_menages_last_month == 0
    assert k.new_menages_last_month_pct_change is None
