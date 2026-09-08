from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_system_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_root: Mapped[bool] = mapped_column(default=False, server_default="false")

    workspaces: Mapped[list[Workspace]] = relationship(secondary="workspace_members", back_populates="members")
