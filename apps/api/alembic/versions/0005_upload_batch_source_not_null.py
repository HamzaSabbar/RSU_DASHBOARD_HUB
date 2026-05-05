"""make upload batch source required

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-05

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE report_upload_batches
            SET systeme_source = COALESCE(NULLIF(metadata_json ->> 'systeme_source', ''), 'system')
            WHERE systeme_source IS NULL
            """
        )
    )
    op.alter_column("report_upload_batches", "systeme_source", nullable=False)


def downgrade() -> None:
    op.alter_column("report_upload_batches", "systeme_source", nullable=True)
