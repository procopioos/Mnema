import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    CurrentUser,
    DbSession,
    MemberWorkspace,
    Storage,
    WorkspaceAdminRequired,
    WorkspaceManagerRequired,
    get_membership,
)
from app.models.audit import AuditAction, AuditLog
from app.models.document import Document
from app.models.user import User
from app.models.workspace import Role, Workspace, WorkspaceMember
from app.schemas.audit import AuditLogListResponse, AuditLogOut
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberPublic,
    WorkspaceMemberUpdate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.services import admin_workspaces as admin_ws_service
from app.services import audit as audit_service
from app.services.workspaces import (
    create_workspace,
    delete_workspace,
    get_workspace_usage,
    rename_workspace,
    serialize_workspace,
)

router = APIRouter()


async def _with_role(db: AsyncSession, user_id: uuid.UUID, workspace: Workspace) -> WorkspaceOut:
    membership = await get_membership(db, user_id, workspace.id)
    document_count, storage_bytes = await get_workspace_usage(db, workspace.id)
    return serialize_workspace(
        workspace,
        membership.role if membership else None,
        document_count,
        storage_bytes,
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


async def _member_public(db: AsyncSession, member: WorkspaceMember) -> WorkspaceMemberPublic:
    user = await db.get(User, member.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member user not found")
    return WorkspaceMemberPublic(
        user_id=member.user_id,
        role=member.role,
        email=user.email,
        full_name=user.full_name,
    )


def _audit_out(
    log: AuditLog, user_email: str | None, user_full_name: str | None, document_filename: str | None
) -> AuditLogOut:
    return AuditLogOut(
        id=log.id,
        action=log.action,
        user_id=log.user_id,
        user_email=user_email,
        user_full_name=user_full_name,
        workspace_id=log.workspace_id,
        document_id=log.document_id,
        document_filename=document_filename,
        detail=log.detail,
        ip=log.ip,
        created_at=log.created_at,
    )


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: CurrentUser, db: DbSession) -> list[WorkspaceOut]:
    rows = (
        await db.execute(
            select(
                Workspace,
                WorkspaceMember.role,
                func.count(func.distinct(Document.id)).label("document_count"),
                func.coalesce(func.sum(Document.size_bytes), 0).label("storage_bytes"),
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .outerjoin(Document, Document.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user.id)
            .group_by(Workspace.id, WorkspaceMember.role)
            .order_by(Workspace.created_at)
        )
    ).all()
    return [
        serialize_workspace(workspace, role, int(document_count), int(storage_bytes))
        for workspace, role, document_count, storage_bytes in rows
    ]


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    payload: WorkspaceCreate,
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceOut:
    workspace = await create_workspace(db, payload.name.strip(), owner_id=user.id)
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_workspace_create,
        workspace_id=workspace.id,
        detail={"name": workspace.name},
    )
    await db.commit()
    await db.refresh(workspace)
    return serialize_workspace(workspace, Role.owner, 0, 0)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace: MemberWorkspace,
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceOut:
    return await _with_role(db, user.id, workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace: WorkspaceAdminRequired,
    payload: WorkspaceUpdate,
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceOut:
    await rename_workspace(db, workspace, payload.name)
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_workspace_rename,
        workspace_id=workspace.id,
        detail={"name": workspace.name},
    )
    await db.commit()
    await db.refresh(workspace)
    return await _with_role(db, user.id, workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace(
    workspace: WorkspaceAdminRequired,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
) -> None:
    await audit_service.record(
        db,
        user.id,
        AuditAction.admin_workspace_delete,
        workspace_id=workspace.id,
        detail={"name": workspace.name},
    )
    await delete_workspace(db, storage, workspace)
    await db.commit()


@router.get("/{workspace_id}/audit", response_model=AuditLogListResponse)
async def list_workspace_audit(
    workspace: WorkspaceManagerRequired,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogListResponse:
    rows, total = await audit_service.list_audit_logs(db, workspace_id=workspace.id, limit=limit, offset=offset)
    return AuditLogListResponse(items=[_audit_out(*row) for row in rows], total=total)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberPublic])
async def list_workspace_members(
    workspace: WorkspaceAdminRequired,
    user: CurrentUser,
    db: DbSession,
) -> list[WorkspaceMemberPublic]:
    members = await admin_ws_service.list_members(db, workspace.id)
    return [await _member_public(db, member) for member in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberPublic,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace: WorkspaceAdminRequired,
    user: CurrentUser,
    payload: WorkspaceMemberAdd,
    db: DbSession,
) -> WorkspaceMemberPublic:
    target = await db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    member = await admin_ws_service.add_member(db, workspace.id, payload.user_id, payload.role)
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_add,
        workspace_id=workspace.id,
        detail={"user_id": str(payload.user_id), "role": payload.role.value},
    )
    await db.commit()
    return await _member_public(db, member)


@router.patch("/{workspace_id}/members/{member_user_id}", response_model=WorkspaceMemberPublic)
async def update_workspace_member(
    workspace: WorkspaceAdminRequired,
    user: CurrentUser,
    member_user_id: uuid.UUID,
    payload: WorkspaceMemberUpdate,
    db: DbSession,
) -> WorkspaceMemberPublic:
    member = await _get_member(db, workspace.id, member_user_id)
    prev_role = member.role
    try:
        member = await admin_ws_service.update_member_role(db, member, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_role,
        workspace_id=workspace.id,
        detail={"user_id": str(member_user_id), "from": prev_role.value, "to": payload.role.value},
    )
    await db.commit()
    return await _member_public(db, member)


@router.delete("/{workspace_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace: WorkspaceAdminRequired,
    user: CurrentUser,
    member_user_id: uuid.UUID,
    db: DbSession,
) -> None:
    member = await _get_member(db, workspace.id, member_user_id)
    try:
        await admin_ws_service.remove_member(db, member)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    await audit_service.record(
        db,
        user.id,
        AuditAction.workspace_member_remove,
        workspace_id=workspace.id,
        detail={"user_id": str(member_user_id)},
    )
    await db.commit()
