"""add folders and tags

Revision ID: b4e2d7a91c30
Revises: 799194686e83
Create Date: 2026-08-26 09:12:40.113258

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4e2d7a91c30"
down_revision: str | Sequence[str] | None = "799194686e83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "folders",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name"),
    )
    op.create_index(op.f("ix_folders_workspace_id"), "folders", ["workspace_id"], unique=False)
    op.create_table(
        "tags",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=7), server_default="#6b7280", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_workspace_id"), "tags", ["workspace_id"], unique=False)
    op.create_index(
        "uq_tags_workspace_name_global",
        "tags",
        ["workspace_id", "name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_tags_workspace_user_name",
        "tags",
        ["workspace_id", "user_id", "name"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_table(
        "document_folders",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "folder_id"),
    )
    op.create_index(op.f("ix_document_folders_document_id"), "document_folders", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_folders_folder_id"), "document_folders", ["folder_id"], unique=False)
    op.create_table(
        "document_tags",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )
    op.create_index(op.f("ix_document_tags_document_id"), "document_tags", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_tags_tag_id"), "document_tags", ["tag_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_document_tags_tag_id"), table_name="document_tags")
    op.drop_index(op.f("ix_document_tags_document_id"), table_name="document_tags")
    op.drop_table("document_tags")
    op.drop_index(op.f("ix_document_folders_folder_id"), table_name="document_folders")
    op.drop_index(op.f("ix_document_folders_document_id"), table_name="document_folders")
    op.drop_table("document_folders")
    op.drop_index("uq_tags_workspace_user_name", table_name="tags")
    op.drop_index("uq_tags_workspace_name_global", table_name="tags")
    op.drop_index(op.f("ix_tags_workspace_id"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_folders_workspace_id"), table_name="folders")
    op.drop_table("folders")
