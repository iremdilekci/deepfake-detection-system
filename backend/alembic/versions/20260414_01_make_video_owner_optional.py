"""Allow anonymous video uploads.

Revision ID: 20260414_01
Revises:
Create Date: 2026-04-14 10:00:00.000000
"""

from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260414_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "videos",
        "owner_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "videos",
        "owner_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
