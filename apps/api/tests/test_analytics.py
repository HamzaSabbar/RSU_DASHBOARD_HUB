from __future__ import annotations

import pandas as pd

from boards.macro_national import analytics, parser


def test_parser_detects_consolidated_from_column(consolidated_xlsx_bytes: bytes) -> None:
    kind = parser.detect_file_kind("donnees_rsu.xlsx", consolidated_xlsx_bytes)
    assert kind is not None
    assert kind.value == "consolidated"


def test_parse_consolidated_shape_and_columns(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    assert set(df.columns) == {
        "month",
        "region",
        "province",
        "inscriptions_rsu_individus",
        "entrants_menage_asd",
        "sortants_menage_asd",
        "entrants_menage_amot",
        "sortants_menage_amot",
        "bloque_fms",
        "bloque_multi",
        "bloque_individuel",
    }
    assert df.shape[0] == 6
    assert set(df["province"].unique()) == {"AZILAL", "BEN MHAMED", "CASABLANCA"}
    assert set(df["month"].unique()) == {"2026-01", "2026-02"}


def test_inscriptions_kpis_from_consolidated(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    insc_df = df.rename(columns={"inscriptions_rsu_individus": "value"})[
        ["province", "month", "value"]
    ]
    k = analytics.compute_inscriptions_kpis(insc_df)
    # total: 100+200+500 + 120+220+550 = 800 + 890 = 1690
    assert k.total_menages == 1690
    # last month (2026-02): 120+220+550 = 890
    assert k.new_menages_last_month == 890
    # previous month (2026-01): 100+200+500 = 800
    expected_pct = round(((890 - 800) / 800) * 100, 2)
    assert k.new_menages_last_month_pct_change == expected_pct


def test_monthly_evolution_chronological(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    insc_df = df.rename(columns={"inscriptions_rsu_individus": "value"})[
        ["province", "month", "value"]
    ]
    points = analytics.compute_monthly_evolution(insc_df)
    months = [p.month for p in points]
    assert months == sorted(months)
    assert points[0].delta is None
    assert points[1].delta == points[1].value - points[0].value


def test_top_provinces_by_inscriptions(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    insc_df = df.rename(columns={"inscriptions_rsu_individus": "value"})[
        ["province", "month", "value"]
    ]
    top = analytics.compute_top_provinces(insc_df, k=3)
    # CASABLANCA: 500+550=1050, BEN MHAMED: 200+220=420, AZILAL: 100+120=220
    assert [p.province for p in top] == ["CASABLANCA", "BEN MHAMED", "AZILAL"]
    assert [p.value for p in top] == [1050, 420, 220]


def test_entries_exits_per_month(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    ee = analytics.compute_entries_exits(df)
    assert len(ee) == 2
    m = {p.month: p for p in ee}
    # 2026-01: entrants = (50+80+200)+(10+20+50) = 330+80 = 410
    assert m["2026-01"].entrants == 410
    # 2026-01: sortants = (30+40+100)+(5+8+20) = 170+33 = 203
    assert m["2026-01"].sortants == 203


def test_region_flux_aggregated_by_region(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    flux = analytics.compute_region_flux(df)
    by_region = {f.region: f for f in flux}
    assert set(by_region) == {"Béni Mellal-Khénifra", "Casablanca-Settat"}
    # Béni Mellal-Khénifra 2 months: entrants_asd=50+80+55+85=270, entrants_amot=10+20+12+22=64 → 334
    assert by_region["Béni Mellal-Khénifra"].entrants == 334


def test_menages_bloques_categories(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    cats = analytics.compute_menages_bloques_categories(df)
    by_cat = {c.category: c.count for c in cats}
    # bloque_fms total: 20+40+80+25+45+85 = 295
    assert by_cat["FMS fraude"] == 295
    assert set(by_cat) == {"FMS fraude", "Multi-noyau procédure", "Individuel procédure"}


def test_top_provinces_bloques(consolidated_xlsx_bytes: bytes) -> None:
    df = parser.parse_consolidated(consolidated_xlsx_bytes)
    top = analytics.compute_top_bloques_regions(df, k=2)
    # CASABLANCA: (80+60+100)+(85+65+110)=240+260=500
    # BEN MHAMED: (40+25+50)+(45+28+55)=115+128=243
    # AZILAL: (20+15+30)+(25+18+35)=65+78=143
    assert top[0].province == "CASABLANCA"
    assert top[0].value == 500
    assert top[1].province == "BEN MHAMED"


def test_empty_dataframe_returns_zeroed_kpis() -> None:
    empty = pd.DataFrame(columns=["province", "month", "value"])
    k = analytics.compute_inscriptions_kpis(empty)
    assert k.total_menages == 0
    assert k.total_personnes == 0
    assert k.new_menages_last_month == 0
    assert k.new_menages_last_month_pct_change is None
