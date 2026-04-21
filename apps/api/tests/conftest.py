from __future__ import annotations

import io

import pytest
from openpyxl import Workbook


@pytest.fixture
def inscriptions_xlsx_bytes() -> bytes:
    """3 provinces × 4 months, matching the stat_nouveaux_inscrits_rnp layout."""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    # row 1: year headers (empty in col A)
    ws.cell(row=1, column=1, value=None)
    ws.cell(row=1, column=2, value=2025)
    ws.cell(row=1, column=3, value=None)
    ws.cell(row=1, column=4, value=None)
    ws.cell(row=1, column=5, value=None)
    # row 2: month abbreviations
    ws.cell(row=2, column=1, value="Province")
    ws.cell(row=2, column=2, value="janv.")
    ws.cell(row=2, column=3, value="févr.")
    ws.cell(row=2, column=4, value="mars")
    ws.cell(row=2, column=5, value="avril")
    # data
    data = [
        ("Casablanca", 1200, 1500, 1800, 2000),
        ("Rabat", 800, 900, 1100, 1300),
        ("Tanger", 300, 350, 400, 500),
    ]
    for i, (prov, *vals) in enumerate(data, start=3):
        ws.cell(row=i, column=1, value=prov)
        for j, v in enumerate(vals, start=2):
            ws.cell(row=i, column=j, value=v)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
