import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.storage import StorageBackend
from app.models.document import Document
from app.models.workspace import Role, Workspace, WorkspaceMember
from app.schemas.workspace import WorkspaceOut


def effective_limits(workspace: Workspace) -> tuple[int, int]:
    settings = get_settings()
    max_documents = (
        workspace.max_documents if workspace.max_documents is not None else settings.max_documents_per_workspace
    )
    max_storage_bytes = (
        workspace.max_storage_bytes
        if workspace.max_storage_bytes is not None
        else settings.max_storage_bytes_per_workspace
    )
    return max_documents, max_storage_bytes


async def get_workspace_usage(db: AsyncSession, workspace_id: uuid.UUID) -> tuple[int, int]:
    document_count = (
        await db.scalar(select(func.count()).select_from(Document).where(Document.workspace_id == workspace_id)) or 0
    )
    storage_bytes = (
        await db.scalar(
            select(func.coalesce(func.sum(Document.size_bytes), 0)).where(Document.workspace_id == workspace_id)
        )
        or 0
    )
    return int(document_count), int(storage_bytes)


def serialize_workspace(
    workspace: Workspace,
    role: Role | None,
    document_count: int,
    storage_bytes: int,
) -> WorkspaceOut:
    max_documents, max_storage_bytes = effective_limits(workspace)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        role=role,
        max_documents=max_documents,
        max_storage_bytes=max_storage_bytes,
        document_count=document_count,
        storage_bytes=storage_bytes,
        created_at=workspace.created_at,
    )


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


async def unique_slug(db: AsyncSession, name: str, exclude_id: uuid.UUID | None = None) -> str:
    base = slugify(name)
    candidate = base

    async def _exists(slug: str) -> bool:
        stmt = select(Workspace.id).where(Workspace.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Workspace.id != exclude_id)
        return await db.scalar(stmt) is not None

    while await _exists(candidate):
        candidate = f"{base}-{uuid.uuid4().hex[:6]}"
    return candidate


async def create_workspace(db: AsyncSession, name: str, owner_id: uuid.UUID) -> Workspace:
    workspace = Workspace(name=name, slug=await unique_slug(db, name), owner_id=owner_id)
    db.add(workspace)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner_id, role=Role.owner))
    await db.flush()
    return workspace


async def rename_workspace(db: AsyncSession, workspace: Workspace, name: str) -> Workspace:
    workspace.name = name.strip()
    workspace.slug = await unique_slug(db, name.strip(), exclude_id=workspace.id)
    await db.flush()
    return workspace


async def delete_workspace(db: AsyncSession, storage: StorageBackend, workspace: Workspace) -> None:
    """Delete a workspace and remove its documents' stored files."""
    keys = (await db.scalars(select(Document.storage_key).where(Document.workspace_id == workspace.id))).all()
    await db.delete(workspace)
    await db.flush()
    for key in keys:
        await storage.delete(key)
