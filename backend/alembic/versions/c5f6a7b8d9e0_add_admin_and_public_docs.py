"""add system admin, root user, and public documents

Revision ID: c5f6a7b8d9e0
Revises: b4e2d7a91c30
Create Date: 2026-09-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5f6a7b8d9e0"
down_revision: str | Sequence[str] | None = "a1c2d3e4f5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("is_system_admin", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("is_root", sa.Boolean(), server_default="false", nullable=False))
    op.create_index("ix_users_is_system_admin", "users", ["is_system_admin"], unique=False)

    op.add_column("documents", sa.Column("is_public", sa.Boolean(), server_default="false", nullable=False))
    op.create_index("ix_documents_is_public", "documents", ["is_public"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_documents_is_public", table_name="documents")
    op.drop_column("documents", "is_public")
    op.drop_index("ix_users_is_system_admin", table_name="users")
    op.drop_column("users", "is_root")
    op.drop_column("users", "is_system_admin")
