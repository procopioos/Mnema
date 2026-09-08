import uuid
from io import BytesIO
from pathlib import Path

import anyio
from arq.connections import ArqRedis
from sqlalchemy import delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.domain.exceptions import (
    InvalidReferenceError,
    QueueUnavailableError,
    QuotaExceededError,
    UnsupportedFileTypeError,
)
from app.domain.formats import ALLOWED_EXTENSIONS, mime_for
from app.infrastructure.storage import StorageBackend
from app.models.document import Document, DocumentPage, DocumentStatus
from app.models.folder import DocumentFolder, Folder
from app.models.tag import DocumentTag, Tag
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.document import DocumentOut
from app.services.tags import visible_to
from app.services.workspaces import effective_limits


def serialize_document(document: Document, viewer_id: uuid.UUID) -> DocumentOut:
    """Serialize a document, hiding other users' personal tags from the viewer."""
    out = DocumentOut.model_validate(document)
    out.tags = [tag for tag in out.tags if tag.user_id is None or tag.user_id == viewer_id]
    return out


def safe_filename(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name.strip().strip('"')
    return (name or "document")[:255]


async def ensure_workspace_quota(
    db: AsyncSession,
    workspace: Workspace,
    incoming_size: int = 0,
) -> None:
    """Raise QuotaExceededError before persisting a new upload."""
    max_documents, max_storage_bytes = effective_limits(workspace)

    if max_documents > 0:
        document_count = (
            await db.scalar(select(func.count()).select_from(Document).where(Document.workspace_id == workspace.id))
            or 0
        )
        if document_count >= max_documents:
            raise QuotaExceededError(
                "documents_count_exceeded",
                f"This workspace allows at most {max_documents} documents",
            )

    if max_storage_bytes > 0:
        used = (
            await db.scalar(
                select(func.coalesce(func.sum(Document.size_bytes), 0)).where(Document.workspace_id == workspace.id)
            )
            or 0
        )
        if used + incoming_size > max_storage_bytes:
            raise QuotaExceededError(
                "storage_exceeded",
                f"This workspace storage limit is {max_storage_bytes} bytes",
            )


async def upload_document(
    db: AsyncSession,
    storage: StorageBackend,
    arq: ArqRedis,
    workspace: Workspace,
    user: User,
    filename: str,
    stream: object,
    is_public: bool = False,
) -> Document:
    """Persist an uploaded file, create the Document row, and enqueue processing."""
    filename = safe_filename(filename)
    if Path(filename).suffix.lstrip(".").lower() not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
    mime_type = mime_for(filename)

    raw = await anyio.to_thread.run_sync(stream.read)
    await ensure_workspace_quota(db, workspace, incoming_size=len(raw))

    document_id = uuid.uuid4()
    key = f"{workspace.id}/{document_id}/{filename}"
    size = await storage.save(key, BytesIO(raw), max_size=get_settings().max_upload_size_bytes)

    document = Document(
        id=document_id,
        workspace_id=workspace.id,
        uploader_id=user.id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size,
        storage_key=key,
        title=Path(filename).stem,
        status=DocumentStatus.pending,
        is_public=is_public,
    )
    db.add(document)
    await db.flush()

    try:
        await arq.enqueue_job("process_document", str(document.id), _queue_name=get_settings().arq_queue_name)
    except Exception:
        await db.rollback()
        await storage.delete(key)
        raise QueueUnavailableError("Could not schedule document processing") from None

    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    status: DocumentStatus | None = None,
    folder_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
    unfiled: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Document], int]:
    conditions = [Document.workspace_id == workspace_id]
    if status is not None:
        conditions.append(Document.status == status)
    if unfiled:
        conditions.append(~exists().where(DocumentFolder.document_id == Document.id))
    elif folder_id is not None:
        conditions.append(
            exists().where(DocumentFolder.document_id == Document.id, DocumentFolder.folder_id == folder_id)
        )
    if tag_id is not None:
        conditions.append(exists().where(DocumentTag.document_id == Document.id, DocumentTag.tag_id == tag_id))
    total = await db.scalar(select(func.count()).select_from(Document).where(*conditions)) or 0
    rows = (
        await db.scalars(
            select(Document)
            .options(selectinload(Document.folders), selectinload(Document.tags))
            .where(*conditions)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(rows), total


async def list_public_documents(
    db: AsyncSession,
    viewer_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Document], int, dict[uuid.UUID, str]]:
    """List public documents from any workspace, along with workspace names."""
    total = await db.scalar(select(func.count()).select_from(Document).where(Document.is_public.is_(True))) or 0
    rows = (
        await db.scalars(
            select(Document)
            .options(selectinload(Document.folders), selectinload(Document.tags))
            .where(Document.is_public.is_(True))
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    workspace_ids = {document.workspace_id for document in rows}
    names: dict[uuid.UUID, str] = {}
    if workspace_ids:
        workspaces = (await db.scalars(select(Workspace).where(Workspace.id.in_(workspace_ids)))).all()
        names = {workspace.id: workspace.name for workspace in workspaces}
    return list(rows), total, names


async def set_document_visibility(
    db: AsyncSession,
    document: Document,
    is_public: bool,
) -> Document:
    document.is_public = is_public
    await db.commit()
    return await _reload_document(db, document.id)


def _dedupe(ids: list[uuid.UUID]) -> list[uuid.UUID]:
    return list(dict.fromkeys(ids))


async def _validate_folders(db: AsyncSession, workspace_id: uuid.UUID, folder_ids: list[uuid.UUID]) -> list[Folder]:
    rows = (
        await db.scalars(select(Folder).where(Folder.workspace_id == workspace_id, Folder.id.in_(folder_ids)))
    ).all()
    found = {folder.id for folder in rows}
    missing = [str(folder_id) for folder_id in folder_ids if folder_id not in found]
    if missing:
        raise InvalidReferenceError(f"Unknown folder(s): {', '.join(missing)}")
    return list(rows)


async def set_document_folders(
    db: AsyncSession,
    document: Document,
    folder_ids: list[uuid.UUID],
) -> Document:
    """Replace the document's folders; returns the document with fresh relationships."""
    unique_ids = _dedupe(folder_ids)
    await _validate_folders(db, document.workspace_id, unique_ids)
    await db.execute(delete(DocumentFolder).where(DocumentFolder.document_id == document.id))
    db.add_all([DocumentFolder(document_id=document.id, folder_id=folder_id) for folder_id in unique_ids])
    await db.commit()
    return await _reload_document(db, document.id)


async def set_document_tags(
    db: AsyncSession,
    document: Document,
    viewer_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> Document:
    """Replace the document's tags (only global or viewer-owned tags allowed)."""
    unique_ids = _dedupe(tag_ids)
    if unique_ids:
        rows = (
            await db.scalars(select(Tag).where(Tag.workspace_id == document.workspace_id, Tag.id.in_(unique_ids)))
        ).all()
        attachable = {tag.id for tag in rows if visible_to(tag, viewer_id)}
        missing = [str(tag_id) for tag_id in unique_ids if tag_id not in attachable]
        if missing:
            raise InvalidReferenceError(f"Unknown or inaccessible tag(s): {', '.join(missing)}")
    await db.execute(delete(DocumentTag).where(DocumentTag.document_id == document.id))
    db.add_all([DocumentTag(document_id=document.id, tag_id=tag_id) for tag_id in unique_ids])
    await db.commit()
    return await _reload_document(db, document.id)


async def _reload_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    result = await db.scalars(
        select(Document)
        .options(selectinload(Document.folders), selectinload(Document.tags))
        .execution_options(populate_existing=True)
        .where(Document.id == document_id)
    )
    return result.one()


async def delete_document(db: AsyncSession, storage: StorageBackend, document: Document) -> None:
    await storage.delete(document.storage_key)
    await db.delete(document)
    await db.commit()


async def list_pages(db: AsyncSession, document_id: uuid.UUID) -> list[DocumentPage]:
    return list(
        (
            await db.scalars(
                select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number)
            )
        ).all()
    )


async def get_page(db: AsyncSession, document_id: uuid.UUID, page_number: int) -> DocumentPage | None:
    return await db.scalar(
        select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
    )
