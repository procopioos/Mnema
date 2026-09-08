"""add documents workspace+created index

Revision ID: a1c2d3e4f5b6
Revises: b4e2d7a91c30
Create Date: 2026-09-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c2d3e4f5b6"
down_revision: str | Sequence[str] | None = "b4e2d7a91c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_workspace_created",
        "documents",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_documents_workspace_created", table_name="documents")
