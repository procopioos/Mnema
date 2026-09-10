import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateEmailError, InvalidInviteCodeError
from app.models.user import User
from app.models.workspace import Role, Workspace, WorkspaceMember
from app.services.workspaces import create_workspace, get_workspace_by_code


async def register_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
    full_name: str,
    workspace_code: str | None = None,
) -> tuple[User, Workspace]:
    email = email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise DuplicateEmailError("Email already registered")

    count = await db.scalar(select(func.count()).select_from(User))
    is_first = count == 0

    user = User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        is_system_admin=is_first,
        is_root=is_first,
    )
    db.add(user)
    await db.flush()

    # First user always gets their own workspace
    if is_first or workspace_code is None:
        first_name = full_name.strip().split(maxsplit=1)[0]
        workspace = await create_workspace(db, f"{first_name}'s Workspace", owner_id=user.id)
    else:
        workspace = await get_workspace_by_code(db, workspace_code.strip())
        if workspace is None:
            raise InvalidInviteCodeError("Workspace not found for the given invite code")
        db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=Role.employee))
        await db.flush()

    return user, workspace


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def get_first_workspace_id(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID | None:
    return await db.scalar(
        select(Workspace.id)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(Workspace.created_at)
        .limit(1)
    )
