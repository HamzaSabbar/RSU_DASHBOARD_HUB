"""report jobs for asynchronous workbook processing

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("id_chargement", sa.String(length=255), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_object_path", sa.String(length=1024), nullable=False),
        sa.Column("normalized_object_path", sa.String(length=1024), nullable=True),
        sa.Column("validation_object_path", sa.String(length=1024), nullable=True),
        sa.Column("dashboard_object_path", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="report_jobs_status_check",
        ),
    )
    op.create_index("ix_report_jobs_created_at", "report_jobs", ["created_at"])
    op.create_index("ix_report_jobs_id_chargement", "report_jobs", ["id_chargement"])
    op.create_index("ix_report_jobs_status", "report_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_report_jobs_status", table_name="report_jobs")
    op.drop_index("ix_report_jobs_id_chargement", table_name="report_jobs")
    op.drop_index("ix_report_jobs_created_at", table_name="report_jobs")
    op.drop_table("report_jobs")
