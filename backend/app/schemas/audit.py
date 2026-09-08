import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.audit import AuditAction


class AuditLogOut(BaseModel):
    id: uuid.UUID
    action: AuditAction
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    user_full_name: str | None = None
    workspace_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    document_filename: str | None = None
    detail: dict | None = None
    ip: str | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
