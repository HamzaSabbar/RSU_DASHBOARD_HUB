"""drop legacy report/data-platform/board tables

The product is now the single RSU KPI dashboard (kpi_* tables from 0007).
Everything below belonged to the removed macro-national report pipeline,
the removed programmes-sociaux-rescoring CSV analytics plane, and the
removed dashboard hub -- confirmed dev/synthetic data only, safe to drop
without a backup/export step (see AGENTS.md migration plan).

This migration is irreversible: downgrade() is a documented no-op rather
than attempting to reconstruct dropped tables/data.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-07

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# FK-dependent order: children before parents.
_LEGACY_TABLES: tuple[str, ...] = (
    # report_* fact/dim tables (children of report_upload_batches / report_jobs)
    "report_amount_rules",
    "report_fms_blocked",
    "report_fms_treatment",
    "report_program_fraud",
    "report_program_rescoring",
    "report_program_flow",
    "report_program_stock",
    "report_rsu_annotations",
    "report_rsu_flow",
    "report_rsu_stock",
    "report_codes",
    "report_provinces",
    "report_regions",
    "report_upload_batches",
    "report_jobs",
    # data_platform tables
    "dataset_quality_checks",
    "dataset_artifacts",
    "data_product_builds",
    "platform_releases",
    "core_dataset_versions",
    "data_source_files",
    "data_source_batches",
    # dashboard-hub tables
    "board_snapshots",
    "uploads",
    "boards",
)


def upgrade() -> None:
    for table in _LEGACY_TABLES:
        op.drop_table(table)


def downgrade() -> None:
    raise RuntimeError(
        "0008_drop_legacy_tables is irreversible: the legacy report/data-platform/"
        "board schema and its data are gone. Restore from a database backup taken "
        "before this migration if you need it back."
    )
