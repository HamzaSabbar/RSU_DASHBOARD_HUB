"""KPI renumbering (closes gaps left by the prior deletions) + NOT-01 formula
overhaul + CQD-02 revert to a plain rouge/orange/total multi-window ratio.

Renumbering (old -> new, table/constraint/index names follow):
  kpi_not_02 -> kpi_not_01 (NOT-02 -> NOT-01, also gains new columns below)
  kpi_not_03 -> kpi_not_02 (NOT-03 -> NOT-02, pure rename)
  kpi_rec_04 -> kpi_rec_03 (REC-04 -> REC-03, pure rename)
  kpi_rec_06 -> kpi_rec_04 (REC-06 -> REC-04, pure rename)
  kpi_rec_08 -> kpi_rec_05 (REC-08 -> REC-05, pure rename)

Postgres does not auto-rename constraints/indexes on `RENAME TABLE`, so each
is renamed explicitly to keep the `kpi_<code>_nk` / `ix_kpi_<code>_<col>`
naming convention consistent with every other table.

Also fixes a latent bug from 0009: the old `kpi_rec_08` table carried a
leftover `kpi_rec_08_period_key` UNIQUE CONSTRAINT (auto-created by the
original model's bare `unique=True` on `period`, before 0009 gave this KPI
géo dimensions) that 0009 never dropped -- harmless only by coincidence
because the synthetic seed data happened to have exactly one row per period.
The real workbook has many rows per period (one per région/province/milieu),
so this stale constraint must go.

Confirmed dev/synthetic data only (same as 0009): NOT-01 and CQD-02 are
TRUNCATEd since their column semantics change.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-10

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Renumbering: table + constraint + index renames -------------------
    # kpi_not_02 -> kpi_not_01 (has region/province indexes)
    op.rename_table("kpi_not_02", "kpi_not_01")
    op.execute("ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_02_pkey TO kpi_not_01_pkey")
    op.execute(
        "ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_02_first_seen_import_id_fkey "
        "TO kpi_not_01_first_seen_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_02_last_import_id_fkey "
        "TO kpi_not_01_last_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_02_nk TO kpi_not_01_nk")
    op.execute("ALTER INDEX ix_kpi_not_02_period RENAME TO ix_kpi_not_01_period")
    op.execute("ALTER INDEX ix_kpi_not_02_region RENAME TO ix_kpi_not_01_region")
    op.execute("ALTER INDEX ix_kpi_not_02_province RENAME TO ix_kpi_not_01_province")

    # kpi_not_03 -> kpi_not_02
    op.rename_table("kpi_not_03", "kpi_not_02")
    op.execute("ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_03_pkey TO kpi_not_02_pkey")
    op.execute(
        "ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_03_first_seen_import_id_fkey "
        "TO kpi_not_02_first_seen_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_03_last_import_id_fkey "
        "TO kpi_not_02_last_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_03_nk TO kpi_not_02_nk")
    op.execute("ALTER INDEX ix_kpi_not_03_period RENAME TO ix_kpi_not_02_period")
    op.execute("ALTER INDEX ix_kpi_not_03_region RENAME TO ix_kpi_not_02_region")
    op.execute("ALTER INDEX ix_kpi_not_03_province RENAME TO ix_kpi_not_02_province")

    # kpi_rec_04 -> kpi_rec_03 (no region/province indexes on this one)
    op.rename_table("kpi_rec_04", "kpi_rec_03")
    op.execute("ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_04_pkey TO kpi_rec_03_pkey")
    op.execute(
        "ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_04_first_seen_import_id_fkey "
        "TO kpi_rec_03_first_seen_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_04_last_import_id_fkey "
        "TO kpi_rec_03_last_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_04_nk TO kpi_rec_03_nk")
    op.execute("ALTER INDEX ix_kpi_rec_04_period RENAME TO ix_kpi_rec_03_period")

    # kpi_rec_06 -> kpi_rec_04
    op.rename_table("kpi_rec_06", "kpi_rec_04")
    op.execute("ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_06_pkey TO kpi_rec_04_pkey")
    op.execute(
        "ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_06_first_seen_import_id_fkey "
        "TO kpi_rec_04_first_seen_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_06_last_import_id_fkey "
        "TO kpi_rec_04_last_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_06_nk TO kpi_rec_04_nk")
    op.execute("ALTER INDEX ix_kpi_rec_06_period RENAME TO ix_kpi_rec_04_period")
    op.execute("ALTER INDEX ix_kpi_rec_06_region RENAME TO ix_kpi_rec_04_region")
    op.execute("ALTER INDEX ix_kpi_rec_06_province RENAME TO ix_kpi_rec_04_province")

    # kpi_rec_08 -> kpi_rec_05
    op.rename_table("kpi_rec_08", "kpi_rec_05")
    op.execute("ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_08_pkey TO kpi_rec_05_pkey")
    op.execute(
        "ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_08_first_seen_import_id_fkey "
        "TO kpi_rec_05_first_seen_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_08_last_import_id_fkey "
        "TO kpi_rec_05_last_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_08_nk TO kpi_rec_05_nk")
    op.execute("ALTER INDEX ix_kpi_rec_08_period RENAME TO ix_kpi_rec_05_period")
    op.execute("ALTER INDEX ix_kpi_rec_08_region RENAME TO ix_kpi_rec_05_region")
    op.execute("ALTER INDEX ix_kpi_rec_08_province RENAME TO ix_kpi_rec_05_province")
    # Latent 0009 bug: drop the stale bare-column unique constraint left over
    # from the original single-column `period` natural key.
    op.drop_constraint("kpi_rec_08_period_key", "kpi_rec_05", type_="unique")

    # --- NOT-01 (post-rename, on kpi_not_01): formula overhaul --------------
    op.execute("TRUNCATE TABLE kpi_not_01")
    op.alter_column(
        "kpi_not_01",
        "notifications_recues_logs",
        new_column_name="chefs_avec_notification_recue",
        nullable=False,
    )
    op.add_column(
        "kpi_not_01", sa.Column("chefs_avec_activite_observee", sa.Integer(), nullable=False)
    )

    # --- CQD-02 revert: back to rouge/orange/total, drop urgency_level ------
    op.execute("TRUNCATE TABLE kpi_cqd_02")
    op.drop_constraint("kpi_cqd_02_nk", "kpi_cqd_02", type_="unique")
    op.drop_column("kpi_cqd_02", "urgency_level")
    op.add_column(
        "kpi_cqd_02", sa.Column("menages_soupconnes_rouge", sa.Integer(), nullable=False)
    )
    op.add_column(
        "kpi_cqd_02", sa.Column("menages_soupconnes_orange", sa.Integer(), nullable=False)
    )
    op.create_unique_constraint(
        "kpi_cqd_02_nk", "kpi_cqd_02", ["period", "region", "province", "milieu"]
    )


def downgrade() -> None:
    # --- CQD-02 ---
    op.drop_constraint("kpi_cqd_02_nk", "kpi_cqd_02", type_="unique")
    op.drop_column("kpi_cqd_02", "menages_soupconnes_orange")
    op.drop_column("kpi_cqd_02", "menages_soupconnes_rouge")
    op.add_column("kpi_cqd_02", sa.Column("urgency_level", sa.String(16), nullable=False))
    op.create_unique_constraint(
        "kpi_cqd_02_nk", "kpi_cqd_02", ["period", "region", "province", "milieu", "urgency_level"]
    )

    # --- NOT-01 ---
    op.drop_column("kpi_not_01", "chefs_avec_activite_observee")
    op.alter_column(
        "kpi_not_01",
        "chefs_avec_notification_recue",
        new_column_name="notifications_recues_logs",
        nullable=True,
    )

    # --- kpi_rec_05 -> kpi_rec_08 ---
    op.create_unique_constraint("kpi_rec_08_period_key", "kpi_rec_05", ["period"])
    op.execute("ALTER INDEX ix_kpi_rec_05_province RENAME TO ix_kpi_rec_08_province")
    op.execute("ALTER INDEX ix_kpi_rec_05_region RENAME TO ix_kpi_rec_08_region")
    op.execute("ALTER INDEX ix_kpi_rec_05_period RENAME TO ix_kpi_rec_08_period")
    op.execute("ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_05_nk TO kpi_rec_08_nk")
    op.execute(
        "ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_05_last_import_id_fkey "
        "TO kpi_rec_08_last_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_05_first_seen_import_id_fkey "
        "TO kpi_rec_08_first_seen_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_05 RENAME CONSTRAINT kpi_rec_05_pkey TO kpi_rec_08_pkey")
    op.rename_table("kpi_rec_05", "kpi_rec_08")

    # --- kpi_rec_04 -> kpi_rec_06 ---
    op.execute("ALTER INDEX ix_kpi_rec_04_province RENAME TO ix_kpi_rec_06_province")
    op.execute("ALTER INDEX ix_kpi_rec_04_region RENAME TO ix_kpi_rec_06_region")
    op.execute("ALTER INDEX ix_kpi_rec_04_period RENAME TO ix_kpi_rec_06_period")
    op.execute("ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_04_nk TO kpi_rec_06_nk")
    op.execute(
        "ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_04_last_import_id_fkey "
        "TO kpi_rec_06_last_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_04_first_seen_import_id_fkey "
        "TO kpi_rec_06_first_seen_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_04 RENAME CONSTRAINT kpi_rec_04_pkey TO kpi_rec_06_pkey")
    op.rename_table("kpi_rec_04", "kpi_rec_06")

    # --- kpi_rec_03 -> kpi_rec_04 ---
    op.execute("ALTER INDEX ix_kpi_rec_03_period RENAME TO ix_kpi_rec_04_period")
    op.execute("ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_03_nk TO kpi_rec_04_nk")
    op.execute(
        "ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_03_last_import_id_fkey "
        "TO kpi_rec_04_last_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_03_first_seen_import_id_fkey "
        "TO kpi_rec_04_first_seen_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_rec_03 RENAME CONSTRAINT kpi_rec_03_pkey TO kpi_rec_04_pkey")
    op.rename_table("kpi_rec_03", "kpi_rec_04")

    # --- kpi_not_02 -> kpi_not_03 ---
    op.execute("ALTER INDEX ix_kpi_not_02_province RENAME TO ix_kpi_not_03_province")
    op.execute("ALTER INDEX ix_kpi_not_02_region RENAME TO ix_kpi_not_03_region")
    op.execute("ALTER INDEX ix_kpi_not_02_period RENAME TO ix_kpi_not_03_period")
    op.execute("ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_02_nk TO kpi_not_03_nk")
    op.execute(
        "ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_02_last_import_id_fkey "
        "TO kpi_not_03_last_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_02_first_seen_import_id_fkey "
        "TO kpi_not_03_first_seen_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_not_02 RENAME CONSTRAINT kpi_not_02_pkey TO kpi_not_03_pkey")
    op.rename_table("kpi_not_02", "kpi_not_03")

    # --- kpi_not_01 -> kpi_not_02 ---
    op.execute("ALTER INDEX ix_kpi_not_01_province RENAME TO ix_kpi_not_02_province")
    op.execute("ALTER INDEX ix_kpi_not_01_region RENAME TO ix_kpi_not_02_region")
    op.execute("ALTER INDEX ix_kpi_not_01_period RENAME TO ix_kpi_not_02_period")
    op.execute("ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_01_nk TO kpi_not_02_nk")
    op.execute(
        "ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_01_last_import_id_fkey "
        "TO kpi_not_02_last_import_id_fkey"
    )
    op.execute(
        "ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_01_first_seen_import_id_fkey "
        "TO kpi_not_02_first_seen_import_id_fkey"
    )
    op.execute("ALTER TABLE kpi_not_01 RENAME CONSTRAINT kpi_not_01_pkey TO kpi_not_02_pkey")
    op.rename_table("kpi_not_01", "kpi_not_02")
