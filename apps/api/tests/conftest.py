from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

_CONSOLIDATED_HEADERS = [
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
]

# month, region, province, insc, entr_asd, sort_asd, entr_amot, sort_amot, blq_fms, blq_multi, blq_indiv
_CONSOLIDATED_ROWS = [
    ("2026-01", "Béni Mellal-Khénifra", "AZILAL",       100, 50, 30, 10, 5,  20, 15, 30),
    ("2026-01", "Béni Mellal-Khénifra", "BEN MHAMED",   200, 80, 40, 20, 8,  40, 25, 50),
    ("2026-01", "Casablanca-Settat",    "CASABLANCA",    500, 200, 100, 50, 20, 80, 60, 100),
    ("2026-02", "Béni Mellal-Khénifra", "AZILAL",       120, 55, 35, 12, 6,  25, 18, 35),
    ("2026-02", "Béni Mellal-Khénifra", "BEN MHAMED",   220, 85, 45, 22, 9,  45, 28, 55),
    ("2026-02", "Casablanca-Settat",    "CASABLANCA",    550, 210, 110, 55, 22, 85, 65, 110),
]


def _make_xlsx(headers: list[str], rows: list[tuple]) -> bytes:
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


@pytest.fixture
def consolidated_xlsx_bytes() -> bytes:
    """3 provinces × 2 regions × 2 months, consolidated format."""
    return _make_xlsx(_CONSOLIDATED_HEADERS, _CONSOLIDATED_ROWS)
