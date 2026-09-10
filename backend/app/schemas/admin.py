import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.workspace import Role


class AdminStatsDocuments(BaseModel):
    total: int = 0
    pending: int = 0
    processing: int = 0
    ready: int = 0
    failed: int = 0


class AdminStatsOut(BaseModel):
    users: int = 0
    workspaces: int = 0
    documents: AdminStatsDocuments = Field(default_factory=AdminStatsDocuments)
    storage_bytes: int = 0
    workspaces_usage: list[AdminWorkspaceOut] = Field(default_factory=list)


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_system_admin: bool
    is_root: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    is_system_admin: bool | None = None


class AdminWorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    owner_id: uuid.UUID | None = None


class AdminWorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    max_documents: int | None = Field(default=None, ge=1)
    max_storage_bytes: int | None = Field(default=None, ge=0)


class AdminWorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    invite_code: str | None = None
    member_count: int = 0
    document_count: int = 0
    storage_bytes: int = 0
    max_documents: int | None = None
    max_storage_bytes: int | None = None
    created_at: datetime


class AdminMemberOut(BaseModel):
    user_id: uuid.UUID
    role: Role
    email: str
    full_name: str


class AdminMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: Role = Role.employee


class AdminMemberUpdate(BaseModel):
    role: Role


class AdminMemberMove(BaseModel):
    from_workspace_id: uuid.UUID
    to_workspace_id: uuid.UUID
    role: Role = Role.employee
