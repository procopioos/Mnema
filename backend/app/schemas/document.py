import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus
from app.schemas.folder import FolderOut
from app.schemas.tag import TagOut


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    uploader_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    title: str | None
    status: DocumentStatus
    error_message: str | None
    page_count: int | None
    is_public: bool = False
    processed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    folders: list[FolderOut] = []
    tags: list[TagOut] = []


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int


class DocumentVisibilityUpdate(BaseModel):
    is_public: bool


class PublicDocumentOut(DocumentOut):
    workspace_name: str


class PublicDocumentListResponse(BaseModel):
    items: list[PublicDocumentOut]
    total: int


class DocumentFoldersUpdate(BaseModel):
    folder_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class DocumentTagsUpdate(BaseModel):
    tag_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class DocumentPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    content: str
    char_count: int | None
