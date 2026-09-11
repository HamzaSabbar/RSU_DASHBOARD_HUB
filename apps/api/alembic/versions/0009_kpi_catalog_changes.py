"""KPI catalogue changes: drop NOT-01/REC-03/REC-05/REC-07, add columns/geo
breakdowns to NOT-02/REC-01/REC-06/REC-08/CQD-01/CQD-02

Confirmed dev/synthetic data only. Tables whose natural key changes are
emptied (`TRUNCATE`) rather than dropped-and-recreated: this reaches the same
end state (no stale rows under an obsolete key shape) while reusing the
table's existing `id`/provenance columns and untouched indexes exactly as-is,
instead of risking a hand-copied `CREATE TABLE` drifting from the original.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-09

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Deleted KPIs -------------------------------------------------
    op.drop_table("kpi_not_01")
    op.drop_table("kpi_rec_03")
    op.drop_table("kpi_rec_05")
    op.drop_table("kpi_rec_07")

    # --- Purely additive columns ---------------------------------------
    op.add_column(
        "kpi_not_02",
        sa.Column("notifications_recues_logs", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kpi_cqd_01",
        sa.Column("suspicions_en_traitement", sa.Integer(), nullable=True),
    )

    # --- REC-01: + region/province/milieu, natural key expands ---------
    op.execute("TRUNCATE TABLE kpi_rec_01")
    op.add_column("kpi_rec_01", sa.Column("region", sa.String(128), nullable=False))
    op.add_column("kpi_rec_01", sa.Column("province", sa.String(128), nullable=False))
    op.add_column("kpi_rec_01", sa.Column("milieu", sa.String(16), nullable=False))
    op.drop_constraint("kpi_rec_01_nk", "kpi_rec_01", type_="unique")
    op.create_unique_constraint(
        "kpi_rec_01_nk",
        "kpi_rec_01",
        ["period", "recourse_motive", "region", "province", "milieu"],
    )
    op.create_index("ix_kpi_rec_01_region", "kpi_rec_01", ["region"])
    op.create_index("ix_kpi_rec_01_province", "kpi_rec_01", ["province"])

    # --- REC-06: + region/province/milieu + reclamations_en_cours -------
    op.execute("TRUNCATE TABLE kpi_rec_06")
    op.add_column("kpi_rec_06", sa.Column("region", sa.String(128), nullable=False))
    op.add_column("kpi_rec_06", sa.Column("province", sa.String(128), nullable=False))
    op.add_column("kpi_rec_06", sa.Column("milieu", sa.String(16), nullable=False))
    op.add_column(
        "kpi_rec_06", sa.Column("reclamations_en_cours", sa.Integer(), nullable=True)
    )
    op.drop_constraint("kpi_rec_06_nk", "kpi_rec_06", type_="unique")
    op.create_unique_constraint(
        "kpi_rec_06_nk",
        "kpi_rec_06",
        ["period", "channel", "region", "province", "milieu"],
    )
    op.create_index("ix_kpi_rec_06_region", "kpi_rec_06", ["region"])
    op.create_index("ix_kpi_rec_06_province", "kpi_rec_06", ["province"])

    # --- REC-08: + region/province/milieu, natural key expands beyond
    # the old single-column unique `period` ------------------------------
    op.execute("TRUNCATE TABLE kpi_rec_08")
    op.add_column("kpi_rec_08", sa.Column("region", sa.String(128), nullable=False))
    op.add_column("kpi_rec_08", sa.Column("province", sa.String(128), nullable=False))
    op.add_column("kpi_rec_08", sa.Column("milieu", sa.String(16), nullable=False))
    op.drop_index("ix_kpi_rec_08_period", table_name="kpi_rec_08")
    op.create_index("ix_kpi_rec_08_period", "kpi_rec_08", ["period"])
    op.create_index("ix_kpi_rec_08_region", "kpi_rec_08", ["region"])
    op.create_index("ix_kpi_rec_08_province", "kpi_rec_08", ["province"])
    op.create_unique_constraint(
        "kpi_rec_08_nk", "kpi_rec_08", ["period", "region", "province", "milieu"]
    )

    # --- CQD-02: + urgency_level, natural key expands -------------------
    op.execute("TRUNCATE TABLE kpi_cqd_02")
    op.add_column("kpi_cqd_02", sa.Column("urgency_level", sa.String(16), nullable=False))
    op.drop_constraint("kpi_cqd_02_nk", "kpi_cqd_02", type_="unique")
    op.create_unique_constraint(
        "kpi_cqd_02_nk",
        "kpi_cqd_02",
        ["period", "region", "province", "milieu", "urgency_level"],
    )


def downgrade() -> None:
    op.drop_constraint("kpi_cqd_02_nk", "kpi_cqd_02", type_="unique")
    op.create_unique_constraint(
        "kpi_cqd_02_nk", "kpi_cqd_02", ["period", "region", "province", "milieu"]
    )
    op.drop_column("kpi_cqd_02", "urgency_level")

    op.drop_constraint("kpi_rec_08_nk", "kpi_rec_08", type_="unique")
    op.drop_index("ix_kpi_rec_08_province", table_name="kpi_rec_08")
    op.drop_index("ix_kpi_rec_08_region", table_name="kpi_rec_08")
    op.drop_index("ix_kpi_rec_08_period", table_name="kpi_rec_08")
    op.create_index("ix_kpi_rec_08_period", "kpi_rec_08", ["period"], unique=True)
    op.drop_column("kpi_rec_08", "milieu")
    op.drop_column("kpi_rec_08", "province")
    op.drop_column("kpi_rec_08", "region")

    op.drop_index("ix_kpi_rec_06_province", table_name="kpi_rec_06")
    op.drop_index("ix_kpi_rec_06_region", table_name="kpi_rec_06")
    op.drop_constraint("kpi_rec_06_nk", "kpi_rec_06", type_="unique")
    op.create_unique_constraint("kpi_rec_06_nk", "kpi_rec_06", ["period", "channel"])
    op.drop_column("kpi_rec_06", "reclamations_en_cours")
    op.drop_column("kpi_rec_06", "milieu")
    op.drop_column("kpi_rec_06", "province")
    op.drop_column("kpi_rec_06", "region")

    op.drop_index("ix_kpi_rec_01_province", table_name="kpi_rec_01")
    op.drop_index("ix_kpi_rec_01_region", table_name="kpi_rec_01")
    op.drop_constraint("kpi_rec_01_nk", "kpi_rec_01", type_="unique")
    op.create_unique_constraint(
        "kpi_rec_01_nk", "kpi_rec_01", ["period", "recourse_motive"]
    )
    op.drop_column("kpi_rec_01", "milieu")
    op.drop_column("kpi_rec_01", "province")
    op.drop_column("kpi_rec_01", "region")

    op.drop_column("kpi_cqd_01", "suspicions_en_traitement")
    op.drop_column("kpi_not_02", "notifications_recues_logs")

    op.create_table(
        "kpi_rec_07",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("complaint_motive", sa.String(128), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("reclamations_en_cours", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "channel", "complaint_motive", "region", "province", name="kpi_rec_07_nk"),
    )
    op.create_index("ix_kpi_rec_07_period", "kpi_rec_07", ["period"])
    op.create_index("ix_kpi_rec_07_province", "kpi_rec_07", ["province"])
    op.create_index("ix_kpi_rec_07_region", "kpi_rec_07", ["region"])

    op.create_table(
        "kpi_rec_05",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("recourse_motive", sa.String(128), nullable=False),
        sa.Column("recours_deposes", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "recourse_motive", name="kpi_rec_05_nk"),
    )
    op.create_index("ix_kpi_rec_05_period", "kpi_rec_05", ["period"])

    op.create_table(
        "kpi_rec_03",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False, unique=True),
        sa.Column("menages_avec_recours_60j", sa.Integer(), nullable=False),
        sa.Column("menages_eligibles_fenetre_60j", sa.Integer(), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_kpi_rec_03_period", "kpi_rec_03", ["period"], unique=True)

    op.create_table(
        "kpi_not_01",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("region", sa.String(128), nullable=False),
        sa.Column("province", sa.String(128), nullable=False),
        sa.Column("milieu", sa.String(16), nullable=False),
        sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("numeros_non_operationnels", sa.Integer(), nullable=False),
        sa.Column("numeros_controles", sa.Integer(), nullable=False),
        sa.Column("injoignables", sa.Integer(), nullable=True),
        sa.Column("titulaire_different", sa.Integer(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("first_seen_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("last_import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("kpi_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("period", "region", "province", "milieu", "gender", name="kpi_not_01_nk"),
    )
    op.create_index("ix_kpi_not_01_region", "kpi_not_01", ["region"])
    op.create_index("ix_kpi_not_01_province", "kpi_not_01", ["province"])
    op.create_index("ix_kpi_not_01_period", "kpi_not_01", ["period"])
