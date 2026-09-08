import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    document_count: int = 0
    created_at: datetime
    updated_at: datetime
