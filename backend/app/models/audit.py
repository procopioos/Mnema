from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDMixin

if TYPE_CHECKING:
    pass


class AuditAction(enum.StrEnum):
    document_view = "document.view"
    document_download = "document.download"
    document_upload = "document.upload"
    document_delete = "document.delete"
    document_visibility = "document.visibility"
    workspace_member_add = "workspace.member.add"
    workspace_member_remove = "workspace.member.remove"
    workspace_member_role = "workspace.member.role"
    auth_login = "auth.login"
    admin_reset = "admin.reset"
    admin_user_update = "admin.user.update"
    admin_workspace_create = "admin.workspace.create"
    admin_workspace_rename = "admin.workspace.rename"
    admin_workspace_delete = "admin.workspace.delete"
    admin_workspace_quota = "admin.workspace.quota"
    admin_workspace_regenerate_code = "admin.workspace.regenerate_code"
    workspace_member_move = "workspace.member.move"


def _action_values(enum_cls: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", values_callable=_action_values), index=True
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
