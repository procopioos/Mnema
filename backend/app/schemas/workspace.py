import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.workspace import Role


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceMemberAdd(BaseModel):
    user_id: uuid.UUID
    role: Role = Role.employee


class WorkspaceMemberUpdate(BaseModel):
    role: Role


class WorkspaceMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: Role


class WorkspaceMemberPublic(BaseModel):
    user_id: uuid.UUID
    role: Role
    email: str
    full_name: str


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    role: Role | None = None
    max_documents: int = 0
    max_storage_bytes: int = 0
    document_count: int = 0
    storage_bytes: int = 0
    created_at: datetime
