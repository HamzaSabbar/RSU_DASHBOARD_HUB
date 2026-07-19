"""platform-wide CSV analytical control plane

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-16

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid() -> sa.Column:
    return sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)


def upgrade() -> None:
    op.create_table(
        "data_source_batches",
        _uuid(),
        sa.Column("source_key", sa.String(64), nullable=False, server_default="rsu-csv"),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("pipeline_version", sa.String(128), nullable=False),
        sa.Column("parameters_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(64), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name="data_source_batches_status_check"),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name="data_source_batches_progress_check"),
    )
    op.create_index("ix_data_source_batches_content_hash", "data_source_batches", ["content_hash"])
    op.create_index("ix_data_source_batches_pipeline_version", "data_source_batches", ["pipeline_version"])
    op.create_index("ix_data_source_batches_status", "data_source_batches", ["status"])
    op.create_index("ix_data_source_batches_created_at", "data_source_batches", ["created_at"])

    op.create_table(
        "data_source_files",
        _uuid(),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_source_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("logical_name", sa.String(128), nullable=False),
        sa.Column("relative_path", sa.String(512), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Numeric(20, 0), nullable=False),
        sa.Column("row_count", sa.Numeric(20, 0), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("schema_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("profile_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.UniqueConstraint("batch_id", "logical_name", name="data_source_files_batch_name_uq"),
    )
    op.create_index("ix_data_source_files_batch_id", "data_source_files", ["batch_id"])

    op.create_table(
        "core_dataset_versions",
        _uuid(),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_source_batches.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("version_key", sa.String(160), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="building"),
        sa.Column("dataset_path", sa.String(1024), nullable=False),
        sa.Column("database_path", sa.String(1024), nullable=False),
        sa.Column("manifest_path", sa.String(1024), nullable=True),
        sa.Column("row_counts_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('building', 'ready', 'failed')", name="core_dataset_versions_status_check"),
    )
    op.create_index("ix_core_dataset_versions_version_key", "core_dataset_versions", ["version_key"], unique=True)
    op.create_index("ix_core_dataset_versions_status", "core_dataset_versions", ["status"])

    op.create_table(
        "data_product_builds",
        _uuid(),
        sa.Column("core_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_slug", sa.String(128), nullable=False),
        sa.Column("product_version", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="building"),
        sa.Column("artifact_path", sa.String(1024), nullable=False),
        sa.Column("row_counts_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('building', 'ready', 'failed')", name="data_product_builds_status_check"),
        sa.UniqueConstraint("core_version_id", "product_slug", "product_version", name="data_product_builds_version_uq"),
    )
    op.create_index("ix_data_product_builds_core_version_id", "data_product_builds", ["core_version_id"])
    op.create_index("ix_data_product_builds_product_slug", "data_product_builds", ["product_slug"])
    op.create_index("ix_data_product_builds_status", "data_product_builds", ["status"])

    op.create_table(
        "dataset_artifacts",
        _uuid(),
        sa.Column("core_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_build_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_product_builds.id", ondelete="CASCADE"), nullable=True),
        sa.Column("layer", sa.String(32), nullable=False),
        sa.Column("artifact_name", sa.String(160), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("relative_path", sa.String(1024), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Numeric(20, 0), nullable=False),
        sa.Column("row_count", sa.Numeric(20, 0), nullable=True),
        sa.Column("schema_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("core_version_id", "artifact_name", name="dataset_artifacts_core_name_uq"),
    )
    op.create_index("ix_dataset_artifacts_core_version_id", "dataset_artifacts", ["core_version_id"])
    op.create_index("ix_dataset_artifacts_product_build_id", "dataset_artifacts", ["product_build_id"])

    op.create_table(
        "dataset_quality_checks",
        _uuid(),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("data_source_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("core_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core_dataset_versions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("check_key", sa.String(160), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("observed_value", sa.String(255), nullable=True),
        sa.Column("expected_value", sa.String(255), nullable=True),
        sa.Column("details_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("severity IN ('info', 'warning', 'error')", name="dataset_quality_checks_severity_check"),
        sa.UniqueConstraint("batch_id", "check_key", name="dataset_quality_checks_batch_key_uq"),
    )
    op.create_index("ix_dataset_quality_checks_batch_id", "dataset_quality_checks", ["batch_id"])
    op.create_index("ix_dataset_quality_checks_core_version_id", "dataset_quality_checks", ["core_version_id"])
    op.create_index("ix_dataset_quality_checks_passed", "dataset_quality_checks", ["passed"])

    op.create_table(
        "platform_releases",
        _uuid(),
        sa.Column("release_key", sa.String(160), nullable=False, unique=True),
        sa.Column("core_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("core_dataset_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("products_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_platform_releases_release_key", "platform_releases", ["release_key"], unique=True)
    op.create_index("ix_platform_releases_core_version_id", "platform_releases", ["core_version_id"])
    op.create_index("ix_platform_releases_is_active", "platform_releases", ["is_active"])
    op.create_index("ix_platform_releases_published_at", "platform_releases", ["published_at"])
    op.create_index("ix_platform_releases_single_active", "platform_releases", ["is_active"], unique=True, postgresql_where=sa.text("is_active IS TRUE"))


def downgrade() -> None:
    op.drop_table("platform_releases")
    op.drop_table("dataset_quality_checks")
    op.drop_table("dataset_artifacts")
    op.drop_table("data_product_builds")
    op.drop_table("core_dataset_versions")
    op.drop_table("data_source_files")
    op.drop_table("data_source_batches")
