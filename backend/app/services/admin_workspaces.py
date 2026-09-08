import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.models.workspace import Role, Workspace, WorkspaceMember


async def list_workspaces_with_metrics(
    db: AsyncSession,
) -> list[tuple[Workspace, int, int, int]]:
    """Return all workspaces with (workspace, member_count, document_count, storage_bytes)."""
    member_count = (
        select(func.count())
        .select_from(WorkspaceMember)
        .where(WorkspaceMember.workspace_id == Workspace.id)
        .correlate(Workspace)
        .scalar_subquery()
        .label("member_count")
    )
    rows = (
        await db.execute(
            select(
                Workspace,
                member_count,
                func.count(func.distinct(Document.id)).label("document_count"),
                func.coalesce(func.sum(Document.size_bytes), 0).label("storage_bytes"),
            )
            .outerjoin(Document, Document.workspace_id == Workspace.id)
            .group_by(Workspace.id)
            .order_by(Workspace.created_at)
        )
    ).all()
    return [(r[0], r[1], r[2], r[3]) for r in rows]


async def create_workspace_as_admin(db: AsyncSession, name: str, owner_id: uuid.UUID | None = None) -> Workspace:
    """Create a workspace owned by a system admin (or the given user), ensuring at least one member."""
    from app.services.workspaces import create_workspace

    if owner_id is None:
        owner_id = await _default_owner(db)
    workspace = await create_workspace(db, name, owner_id=owner_id)
    await db.flush()
    return workspace


async def _default_owner(db: AsyncSession) -> uuid.UUID:
    user = await db.scalar(select(User).order_by(User.created_at).limit(1))
    if user is None:
        raise ValueError("No user available to own the workspace")
    return user.id


async def rename_workspace(db: AsyncSession, workspace: Workspace, name: str) -> Workspace:
    from app.services.workspaces import unique_slug

    workspace.name = name.strip()
    workspace.slug = await unique_slug(db, name.strip())
    await db.flush()
    return workspace


async def delete_workspace_as_admin(db: AsyncSession, workspace: Workspace) -> None:
    await db.delete(workspace)
    await db.flush()


async def workspace_usage(db: AsyncSession, workspace_id: uuid.UUID) -> tuple[int, int, int]:
    """Return (member_count, document_count, storage_bytes) for a single workspace."""
    from app.services.workspaces import get_workspace_usage

    member_count = (
        await db.scalar(
            select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        or 0
    )
    document_count, storage_bytes = await get_workspace_usage(db, workspace_id)
    return int(member_count), document_count, storage_bytes


async def list_members(db: AsyncSession, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
    return list(
        (
            await db.scalars(
                select(WorkspaceMember)
                .where(WorkspaceMember.workspace_id == workspace_id)
                .order_by(WorkspaceMember.created_at)
            )
        ).all()
    )


async def add_member(db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID, role: Role) -> WorkspaceMember:
    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if existing is not None:
        existing.role = role
        await db.flush()
        return existing
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    db.add(member)
    await db.flush()
    return member


async def update_member_role(db: AsyncSession, member: WorkspaceMember, role: Role) -> WorkspaceMember:
    if member.role == Role.owner and role != Role.owner:
        raise ValueError("Cannot change the role of the workspace owner")
    member.role = role
    await db.flush()
    return member


async def remove_member(db: AsyncSession, member: WorkspaceMember) -> None:
    if member.role == Role.owner:
        raise ValueError("Cannot remove the workspace owner")
    await db.delete(member)
    await db.flush()
