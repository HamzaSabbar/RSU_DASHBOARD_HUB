"""CQD-02: menages_distincts_soupconnes becomes nullable.

The real workbook leaves "Nombre total de ménages soupçonnés" blank on every
row -- rouge/orange are the only counts the source team actually fills in.
The KPI's "total" ratio window is now derived as rouge + orange at query
time (see kpi/specs.py, kpi/analytics.py `_sum_fields`), so this column is
no longer load-bearing; it's kept only for an optional SumEquals cross-check
when a future import does fill it in.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-10

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("kpi_cqd_02", "menages_distincts_soupconnes", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE kpi_cqd_02 SET menages_distincts_soupconnes = 0 WHERE menages_distincts_soupconnes IS NULL")
    op.alter_column("kpi_cqd_02", "menages_distincts_soupconnes", nullable=False)
