"""add workspace quotas

Revision ID: e2f3a4b5c6d7
Revises: b1e0a1a2f3c4
Create Date: 2026-09-08 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: str | Sequence[str] | None = "b1e0a1a2f3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("workspaces", sa.Column("max_documents", sa.Integer(), nullable=True))
    op.add_column("workspaces", sa.Column("max_storage_bytes", sa.BigInteger(), nullable=True))
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'admin.workspace.quota'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workspaces", "max_storage_bytes")
    op.drop_column("workspaces", "max_documents")
