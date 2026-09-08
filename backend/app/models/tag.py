from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Tag(UUIDMixin, TimestampMixin, Base):
    """A colored label scoped to a workspace.

    ``user_id is None`` marks a global tag visible to every workspace member;
    a non-null ``user_id`` restricts visibility to that single user.
    """

    __tablename__ = "tags"
    __table_args__ = (
        Index(
            "uq_tags_workspace_name_global",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
        Index(
            "uq_tags_workspace_user_name",
            "workspace_id",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), server_default="#6b7280")


class DocumentTag(Base):
    """Association between documents and tags (many-to-many)."""

    __tablename__ = "document_tags"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True)
