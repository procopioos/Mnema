import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.deps import (
    CurrentUser,
    DbSession,
    DocumentManageResource,
    DocumentReadResource,
    MemberWorkspace,
    Storage,
)
from app.domain.exceptions import StoredFileMissingError
from app.infrastructure.queue import ArqRedisDep
from app.models.audit import AuditAction
from app.models.document import Document, DocumentPage, DocumentStatus
from app.schemas.document import (
    DocumentFoldersUpdate,
    DocumentListResponse,
    DocumentOut,
    DocumentPageOut,
    DocumentTagsUpdate,
    DocumentVisibilityUpdate,
    PublicDocumentListResponse,
    PublicDocumentOut,
)
from app.services import audit as audit_service
from app.services import documents as documents_service

router = APIRouter()


@router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace: MemberWorkspace,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    arq: ArqRedisDep,
    file: Annotated[UploadFile, File()],
    is_public: Annotated[bool, Form()] = False,
) -> Document:
    document = await documents_service.upload_document(
        db,
        storage,
        arq,
        workspace,
        user,
        file.filename or "",
        file.file,
        is_public=is_public,
    )
    await audit_service.record(
        db,
        user.id,
        AuditAction.document_upload,
        workspace_id=workspace.id,
        document_id=document.id,
        detail={"filename": document.filename},
    )
    return document


@router.get("/workspaces/{workspace_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    workspace: MemberWorkspace,
    user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    folder_id: Annotated[uuid.UUID | None, Query()] = None,
    tag_id: Annotated[uuid.UUID | None, Query()] = None,
    unfiled: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    items, total = await documents_service.list_documents(
        db,
        workspace.id,
        status=status_filter,
        folder_id=folder_id,
        tag_id=tag_id,
        unfiled=unfiled,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(
        items=[documents_service.serialize_document(item, user.id) for item in items],
        total=total,
    )


@router.get("/documents/public", response_model=PublicDocumentListResponse)
async def list_public_documents(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PublicDocumentListResponse:
    items, total, workspace_names = await documents_service.list_public_documents(
        db, user.id, limit=limit, offset=offset
    )
    return PublicDocumentListResponse(
        items=[
            PublicDocumentOut(
                **documents_service.serialize_document(item, user.id).model_dump(),
                workspace_name=workspace_names.get(item.workspace_id, ""),
            )
            for item in items
        ],
        total=total,
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document: DocumentReadResource, user: CurrentUser, db: DbSession) -> DocumentOut:
    await audit_service.record(
        db,
        user.id,
        AuditAction.document_view,
        workspace_id=document.workspace_id,
        document_id=document.id,
    )
    return documents_service.serialize_document(document, user.id)


@router.patch("/documents/{document_id}/visibility", response_model=DocumentOut)
async def set_document_visibility(
    document: DocumentManageResource,
    user: CurrentUser,
    payload: DocumentVisibilityUpdate,
    db: DbSession,
) -> Document:
    updated = await documents_service.set_document_visibility(db, document, payload.is_public)
    await audit_service.record(
        db,
        user.id,
        AuditAction.document_visibility,
        workspace_id=document.workspace_id,
        document_id=document.id,
        detail={"is_public": payload.is_public},
    )
    return updated


@router.put("/documents/{document_id}/folders", response_model=DocumentOut)
async def set_document_folders(
    document: DocumentManageResource,
    payload: DocumentFoldersUpdate,
    db: DbSession,
) -> Document:
    return await documents_service.set_document_folders(db, document, payload.folder_ids)


@router.put("/documents/{document_id}/tags", response_model=DocumentOut)
async def set_document_tags(
    document: DocumentManageResource,
    user: CurrentUser,
    payload: DocumentTagsUpdate,
    db: DbSession,
) -> Document:
    return await documents_service.set_document_tags(db, document, user.id, payload.tag_ids)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document: DocumentManageResource,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
) -> None:
    await audit_service.record(
        db,
        user.id,
        AuditAction.document_delete,
        workspace_id=document.workspace_id,
        document_id=document.id,
        detail={"filename": document.filename},
    )
    await documents_service.delete_document(db, storage, document)


@router.get("/documents/{document_id}/pages", response_model=list[DocumentPageOut])
async def list_pages(document: DocumentReadResource, db: DbSession) -> list[DocumentPage]:
    return await documents_service.list_pages(db, document.id)


@router.get("/documents/{document_id}/pages/{page_number}", response_model=DocumentPageOut)
async def get_page(page_number: int, document: DocumentReadResource, db: DbSession) -> DocumentPage:
    page = await documents_service.get_page(db, document.id, page_number)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.get("/documents/{document_id}/file")
async def get_file(
    document: DocumentReadResource,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
) -> FileResponse:
    try:
        path = await storage.open(document.storage_key)
    except FileNotFoundError:
        raise StoredFileMissingError("Stored file not found") from None
    await audit_service.record(
        db,
        user.id,
        AuditAction.document_download,
        workspace_id=document.workspace_id,
        document_id=document.id,
    )
    headers = {"Content-Disposition": f'inline; filename="{document.filename}"'}
    return FileResponse(path, media_type=document.mime_type, headers=headers)
