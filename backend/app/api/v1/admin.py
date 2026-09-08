import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.workspaces import _audit_out
from app.core.deps import DbSession, Storage, SystemAdmin
from app.models.audit import AuditAction
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.admin import (
    AdminMemberAdd,
    AdminMemberOut,
    AdminMemberUpdate,
    AdminStatsOut,
    AdminUserOut,
    AdminUserUpdate,
    AdminWorkspaceCreate,
    AdminWorkspaceOut,
    AdminWorkspaceUpdate,
)
from app.schemas.audit import AuditLogListResponse
from app.services import admin_workspaces as admin_ws_service
from app.services import audit as audit_service
from app.services.admin import reset_app

router = APIRouter()


async def _require_admin_for_user(target_user_id: uuid.UUID, user: User, db: AsyncSession) -> User:
    if not user.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    target = await db.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.is_root and user.id != target.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify root admin")
    return target


async def _get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def _admin_workspace_out(
    workspace: Workspace,
    member_count: int,
    document_count: int,
    storage_bytes: int,
) -> AdminWorkspaceOut:
    return AdminWorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        owner_id=workspace.owner_id,
        member_count=member_count,
        document_count=document_count,
        storage_bytes=storage_bytes,
        max_documents=workspace.max_documents,
        max_storage_bytes=workspace.max_storage_bytes,
        created_at=workspace.created_at,
    )


async def _member_out(db: AsyncSession, member: WorkspaceMember) -> AdminMemberOut:
    user = await db.get(User, member.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member user not found")
    return AdminMemberOut(
        user_id=member.user_id,
        role=member.role,
        email=user.email,
        full_name=user.full_name,
    )


async def _get_member(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID) -> WorkspaceMember:
    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")
    return member


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_endpoint(
    user: SystemAdmin,
    db: DbSession,
    storage: Storage,
) -> None:
    await audit_service.record(db, user.id, AuditAction.admin_reset)
    await reset_app(db, storage)


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    user: SystemAdmin,
    db: DbSession,
) -> dict:
    user_count = await db.scalar(select(func.count()).select_from(User)) or 0
    workspace_count = await db.scalar(select(func.count()).select_from(Workspace)) or 0
    doc_total = await db.scalar(select(func.count()).select_from(Document)) or 0
    doc_pending = (
        await db.scalar(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.pending))
        or 0
    )
    doc_processing = (
        await db.scalar(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.processing))
        or 0
    )
    doc_ready = (
        await db.scalar(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.ready)) or 0
    )
    doc_failed = (
        await db.scalar(select(func.count()).select_from(Document).where(Document.status == DocumentStatus.failed)) or 0
    )
    storage_bytes = await db.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0))) or 0
    workspaces_usage = [_admin_workspace_out(*row) for row in await admin_ws_service.list_workspaces_with_metrics(db)]
    return {
        "users": user_count,
        "workspaces": workspace_count,
        "documents": {
            "total": doc_total,
            "pending": doc_pending,
            "processing": doc_processing,
            "ready": doc_ready,
            "failed": doc_failed,
        },
        "storage_bytes": storage_bytes,
        "workspaces_usage": workspaces_usage,
    }


@router.get("/audit", response_model=AuditLogListResponse)
async def admin_audit(
    user: SystemAdmin,
    db: DbSession,
    workspace_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogListResponse:
    rows, total = await audit_service.list_audit_logs(db, workspace_id=workspace_id, limit=limit, offset=offset)
    return AuditLogListResponse(items=[_audit_out(*row) for row in rows], total=total)


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    user: SystemAdmin,
    db: DbSession,
    q: Annotated[str | None, Query()] = None,
) -> list[User]:
    stmt = select(User).order_by(User.created_at)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(User.email.ilike(pattern) | User.full_name.ilike(pattern))
    return list((await db.scalars(stmt)).all())


@router.patch("/users/{target_user_id}", response_model=AdminUserOut)
async def update_user(
    target_user_id: uuid.UUID,
    payload: AdminUserUpdate,
    user: SystemAdmin,
    db: DbSession,
) -> User:
    target = await _require_admin_for_user(target_user_id, user, db)
    if payload.is_system_admin is not None:
        if target.is_root and not payload.is_system_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot demote root admin")
        target.is_system_admin = payload.is_system_admin
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_user_update,
        workspace_id=None,
        detail={"user_id": str(target.id), "is_system_admin": target.is_system_admin},
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/workspaces", response_model=list[AdminWorkspaceOut])
async def list_admin_workspaces(
    user: SystemAdmin,
    db: DbSession,
) -> list[AdminWorkspaceOut]:
    metrics = await admin_ws_service.list_workspaces_with_metrics(db)
    return [
        _admin_workspace_out(workspace, member_count, document_count, storage_bytes)
        for workspace, member_count, document_count, storage_bytes in metrics
    ]


@router.post("/workspaces", response_model=AdminWorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_admin_workspace(
    payload: AdminWorkspaceCreate,
    user: SystemAdmin,
    db: DbSession,
) -> AdminWorkspaceOut:
    if payload.owner_id is not None:
        owner = await db.get(User, payload.owner_id)
        if owner is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner user not found")
    workspace = await admin_ws_service.create_workspace_as_admin(db, payload.name, payload.owner_id)
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_workspace_create,
        workspace_id=workspace.id,
        detail={"name": workspace.name},
    )
    await db.commit()
    await db.refresh(workspace)
    member_count = (
        await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        )
        or 0
    )
    return _admin_workspace_out(workspace, member_count, 0, 0)


@router.patch("/workspaces/{workspace_id}", response_model=AdminWorkspaceOut)
async def update_admin_workspace(
    workspace_id: uuid.UUID,
    payload: AdminWorkspaceUpdate,
    user: SystemAdmin,
    db: DbSession,
) -> AdminWorkspaceOut:
    workspace = await _get_workspace(db, workspace_id)

    if payload.name is not None:
        workspace = await admin_ws_service.rename_workspace(db, workspace, payload.name)
        await audit_service.record(
            db,
            user.id,
            AuditAction.admin_workspace_rename,
            workspace_id=workspace.id,
            detail={"name": workspace.name},
        )
    if payload.max_documents is not None or payload.max_storage_bytes is not None:
        if payload.max_documents is not None:
            workspace.max_documents = payload.max_documents
        if payload.max_storage_bytes is not None:
            workspace.max_storage_bytes = payload.max_storage_bytes
        await audit_service.record(
            db,
            user.id,
            AuditAction.admin_workspace_quota,
            workspace_id=workspace.id,
            detail={
                "max_documents": workspace.max_documents,
                "max_storage_bytes": workspace.max_storage_bytes,
            },
        )
    await db.commit()
    await db.refresh(workspace)
    member_count, document_count, storage_bytes = await admin_ws_service.workspace_usage(db, workspace.id)
    return _admin_workspace_out(workspace, member_count, document_count, storage_bytes)


@router.delete("/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_workspace(
    workspace_id: uuid.UUID,
    user: SystemAdmin,
    db: DbSession,
) -> None:
    workspace = await _get_workspace(db, workspace_id)
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_workspace_delete,
        workspace_id=workspace.id,
        detail={"name": workspace.name},
    )
    await admin_ws_service.delete_workspace_as_admin(db, workspace)
    await db.commit()


@router.get("/workspaces/{workspace_id}/members", response_model=list[AdminMemberOut])
async def list_workspace_members(
    workspace_id: uuid.UUID,
    user: SystemAdmin,
    db: DbSession,
) -> list[AdminMemberOut]:
    await _get_workspace(db, workspace_id)
    members = await admin_ws_service.list_members(db, workspace_id)
    return [await _member_out(db, m) for m in members]


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=AdminMemberOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: uuid.UUID,
    payload: AdminMemberAdd,
    user: SystemAdmin,
    db: DbSession,
) -> AdminMemberOut:
    await _get_workspace(db, workspace_id)
    target = await db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    member = await admin_ws_service.add_member(db, workspace_id, payload.user_id, payload.role)
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_add,
        workspace_id=workspace_id,
        detail={"user_id": str(payload.user_id), "role": payload.role.value},
    )
    await db.commit()
    return await _member_out(db, member)


@router.patch(
    "/workspaces/{workspace_id}/members/{member_user_id}",
    response_model=AdminMemberOut,
)
async def update_workspace_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: AdminMemberUpdate,
    user: SystemAdmin,
    db: DbSession,
) -> AdminMemberOut:
    await _get_workspace(db, workspace_id)
    member = await _get_member(db, workspace_id, member_user_id)
    prev_role = member.role
    try:
        member = await admin_ws_service.update_member_role(db, member, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_role,
        workspace_id=workspace_id,
        detail={"user_id": str(member_user_id), "from": prev_role.value, "to": payload.role.value},
    )
    await db.commit()
    return await _member_out(db, member)


@router.delete(
    "/workspaces/{workspace_id}/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_workspace_member(
    workspace_id: uuid.UUID,
    member_user_id: uuid.UUID,
    user: SystemAdmin,
    db: DbSession,
) -> None:
    await _get_workspace(db, workspace_id)
    member = await _get_member(db, workspace_id, member_user_id)
    try:
        await admin_ws_service.remove_member(db, member)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_remove,
        workspace_id=workspace_id,
        detail={"user_id": str(member_user_id)},
    )
    await db.commit()
