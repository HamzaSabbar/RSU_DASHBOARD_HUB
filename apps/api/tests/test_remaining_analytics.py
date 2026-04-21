from __future__ import annotations

import io

from openpyxl import Workbook

from boards.macro_national import analytics, parser


def _xlsx_from_rows(headers: list[str], rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    for j, h in enumerate(headers, start=1):
        ws.cell(1, j, h)
    for i, row in enumerate(rows, start=2):
        for j, v in enumerate(row, start=1):
            ws.cell(i, j, v)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_fms_analytics_sums_buckets() -> None:
    content = _xlsx_from_rows(
        ["type_famille", "niveau_risque", "doute_confirme", "doute_leve"],
        [
            ["Individuels", "Élevé", 100, 200],
            ["Individuels", "Moyen", 50, 400],
            ["Mariés avec enfants", "Élevé", 30, 120],
        ],
    )
    df = parser.parse_traitement_fms(content)
    kpis = analytics.compute_fms_kpis(df)
    assert kpis.doute_confirme == 180
    assert kpis.doute_leve == 720
    assert kpis.demandes_traitees == 900
    buckets = analytics.compute_fms_buckets(df)
    assert len(buckets) == 3


def test_flux_regions_parse_and_project() -> None:
    content = _xlsx_from_rows(
        ["region", "entrants", "sortants"],
        [["Casablanca-Settat", 1200, 300], ["Rabat-Salé-Kénitra", 800, 150]],
    )
    df = parser.parse_flux_regions(content)
    flux = analytics.compute_region_flux(df)
    assert {f.region for f in flux} == {"Casablanca-Settat", "Rabat-Salé-Kénitra"}
    assert sum(f.entrants for f in flux) == 2000


def test_menages_bloques_categories_and_top() -> None:
    content = _xlsx_from_rows(
        [
            "region",
            "bloques",
            "fms_fraude",
            "multi_noyau_procedure",
            "individuel_procedure",
        ],
        [
            ["Casablanca-Settat", 500, 200, 150, 150],
            ["Rabat-Salé-Kénitra", 300, 100, 100, 100],
            ["Tanger-Tétouan-Al Hoceima", 200, 80, 60, 60],
        ],
    )
    df = parser.parse_menages_bloques_regions(content)
    cats = analytics.compute_menages_bloques_categories(df)
    assert {c.category for c in cats} == {
        "FMS fraude",
        "Multi-noyau procédure",
        "Individuel procédure",
    }
    by_cat = {c.category: c.count for c in cats}
    assert by_cat["FMS fraude"] == 380
    top = analytics.compute_top_bloques_regions(df, k=2)
    assert [t.province for t in top] == ["Casablanca-Settat", "Rabat-Salé-Kénitra"]


def test_economie_budgetaire_scalar_parse() -> None:
    content = _xlsx_from_rows(
        ["fraude", "rescoring", "total"],
        [[1_000_000, 2_500_000, 3_500_000]],
    )
    values = parser.parse_economie_budgetaire(content)
    eb = analytics.compute_economie_budgetaire(values)
    assert eb.fraude == 1_000_000
    assert eb.rescoring == 2_500_000
    assert eb.total == 3_500_000
