import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions import DuplicateEmailError
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.workspaces import create_workspace


async def register_user(
    db: AsyncSession,
    email: str,
    password_hash: str,
    full_name: str,
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

    first_name = full_name.strip().split(maxsplit=1)[0]
    workspace = await create_workspace(db, f"{first_name}'s Workspace", owner_id=user.id)
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
