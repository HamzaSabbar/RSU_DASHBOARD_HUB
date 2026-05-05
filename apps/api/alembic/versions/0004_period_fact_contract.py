"""period fact contract for cumulative dashboard

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-05

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_report_upload_batches_active_id_chargement", table_name="report_upload_batches")
    op.add_column("report_upload_batches", sa.Column("systeme_source", sa.String(length=255), nullable=True))
    op.create_index("ix_report_upload_batches_systeme_source", "report_upload_batches", ["systeme_source"])
    op.create_index(
        "ix_report_upload_batches_active_source_period",
        "report_upload_batches",
        ["systeme_source", "period_start", "period_end"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )

    op.add_column(
        "report_rsu_flow",
        sa.Column("code_registre", sa.String(length=64), nullable=False, server_default="RNP"),
    )
    op.alter_column("report_rsu_flow", "code_registre", server_default=None)
    op.create_index("ix_report_rsu_flow_code_registre", "report_rsu_flow", ["code_registre"])

    for table in ("report_fms_treatment", "report_fms_blocked"):
        op.add_column(table, sa.Column("debut_periode", sa.Date(), nullable=True))
        op.add_column(table, sa.Column("fin_periode", sa.Date(), nullable=True))
        op.add_column(table, sa.Column("date_evenement", sa.Date(), nullable=True))
        op.add_column(table, sa.Column("mois_evenement", sa.String(length=7), nullable=True))
        op.create_index(f"ix_{table}_debut_periode", table, ["debut_periode"])
        op.create_index(f"ix_{table}_fin_periode", table, ["fin_periode"])
        op.create_index(f"ix_{table}_date_evenement", table, ["date_evenement"])
        op.create_index(f"ix_{table}_mois_evenement", table, ["mois_evenement"])


def downgrade() -> None:
    for table in ("report_fms_blocked", "report_fms_treatment"):
        op.drop_index(f"ix_{table}_mois_evenement", table_name=table)
        op.drop_index(f"ix_{table}_date_evenement", table_name=table)
        op.drop_index(f"ix_{table}_fin_periode", table_name=table)
        op.drop_index(f"ix_{table}_debut_periode", table_name=table)
        op.drop_column(table, "mois_evenement")
        op.drop_column(table, "date_evenement")
        op.drop_column(table, "fin_periode")
        op.drop_column(table, "debut_periode")

    op.drop_index("ix_report_rsu_flow_code_registre", table_name="report_rsu_flow")
    op.drop_column("report_rsu_flow", "code_registre")

    op.drop_index("ix_report_upload_batches_active_source_period", table_name="report_upload_batches")
    op.drop_index("ix_report_upload_batches_systeme_source", table_name="report_upload_batches")
    op.drop_column("report_upload_batches", "systeme_source")
    op.create_index(
        "ix_report_upload_batches_active_id_chargement",
        "report_upload_batches",
        ["id_chargement"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
