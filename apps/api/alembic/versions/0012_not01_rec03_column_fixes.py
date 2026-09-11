"""Align NOT-01 and REC-03 with the real "VF" seed workbook.

NOT-01: the source dropped its "Nombre total d'OTP réussis" column entirely
(and renamed the OTP header to "Nb de Chefs avec ≥1 OTP réussi", a pure
spec.py text change with no schema impact) -- drop the now-unused column.

REC-03: the source gained région/province/milieu dimensions, matching its
siblings REC-01/REC-04/REC-05. Natural key expands, so (dev/synthetic data
only, same pattern as prior migrations) the table is truncated.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-11

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("kpi_not_01", "total_otp_reussis")

    op.execute("TRUNCATE TABLE kpi_rec_03")
    op.add_column("kpi_rec_03", sa.Column("region", sa.String(128), nullable=False))
    op.add_column("kpi_rec_03", sa.Column("province", sa.String(128), nullable=False))
    op.add_column("kpi_rec_03", sa.Column("milieu", sa.String(16), nullable=False))
    op.drop_constraint("kpi_rec_03_nk", "kpi_rec_03", type_="unique")
    op.create_unique_constraint(
        "kpi_rec_03_nk",
        "kpi_rec_03",
        ["period", "recourse_motive", "region", "province", "milieu"],
    )
    op.create_index("ix_kpi_rec_03_region", "kpi_rec_03", ["region"])
    op.create_index("ix_kpi_rec_03_province", "kpi_rec_03", ["province"])


def downgrade() -> None:
    op.drop_index("ix_kpi_rec_03_province", table_name="kpi_rec_03")
    op.drop_index("ix_kpi_rec_03_region", table_name="kpi_rec_03")
    op.drop_constraint("kpi_rec_03_nk", "kpi_rec_03", type_="unique")
    op.create_unique_constraint(
        "kpi_rec_03_nk", "kpi_rec_03", ["period", "recourse_motive"]
    )
    op.drop_column("kpi_rec_03", "milieu")
    op.drop_column("kpi_rec_03", "province")
    op.drop_column("kpi_rec_03", "region")

    op.add_column("kpi_not_01", sa.Column("total_otp_reussis", sa.Integer(), nullable=True))
