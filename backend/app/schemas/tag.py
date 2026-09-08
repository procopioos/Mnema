import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TAG_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"
TagScope = Literal["global", "user"]


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#6b7280", pattern=TAG_COLOR_PATTERN)
    scope: TagScope = "user"


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=TAG_COLOR_PATTERN)


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID | None
    name: str
    color: str
    created_at: datetime
    updated_at: datetime
