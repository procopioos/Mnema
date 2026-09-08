import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateNameError
from app.models.document import Document
from app.models.folder import DocumentFolder, Folder
from app.models.workspace import Workspace


async def _name_taken(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    name: str,
    exclude_folder_id: uuid.UUID | None = None,
) -> bool:
    conditions = [Folder.workspace_id == workspace_id, Folder.name == name]
    if exclude_folder_id is not None:
        conditions.append(Folder.id != exclude_folder_id)
    return await db.scalar(select(Folder.id).where(*conditions).limit(1)) is not None


async def create_folder(db: AsyncSession, workspace: Workspace, name: str) -> Folder:
    name = name.strip()
    if await _name_taken(db, workspace.id, name):
        raise DuplicateNameError(f"Folder '{name}' already exists")
    folder = Folder(workspace_id=workspace.id, name=name)
    db.add(folder)
    await db.flush()
    await db.commit()
    return folder


async def rename_folder(db: AsyncSession, folder: Folder, name: str) -> Folder:
    name = name.strip()
    if await _name_taken(db, folder.workspace_id, name, exclude_folder_id=folder.id):
        raise DuplicateNameError(f"Folder '{name}' already exists")
    folder.name = name
    await db.flush()
    await db.commit()
    await db.refresh(folder)
    return folder


async def delete_folder(db: AsyncSession, folder: Folder) -> None:
    await db.delete(folder)
    await db.flush()
    await db.commit()


async def list_folders_with_counts(db: AsyncSession, workspace_id: uuid.UUID) -> list[tuple[Folder, int]]:
    counts = (
        select(DocumentFolder.folder_id.label("folder_id"), func.count().label("doc_count"))
        .join(Document, Document.id == DocumentFolder.document_id)
        .where(Document.workspace_id == workspace_id)
        .group_by(DocumentFolder.folder_id)
        .subquery()
    )
    rows = await db.execute(
        select(Folder, func.coalesce(counts.c.doc_count, 0))
        .outerjoin(counts, counts.c.folder_id == Folder.id)
        .where(Folder.workspace_id == workspace_id)
        .order_by(Folder.name)
    )
    return [(folder, count) for folder, count in rows.all()]
