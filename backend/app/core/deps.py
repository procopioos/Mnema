import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.infrastructure.storage import StorageBackend, get_storage
from app.models.document import Document
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User
from app.models.workspace import Role, Workspace, WorkspaceMember

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Credentials, db: DbSession) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    subject = decode_token(credentials.credentials, "access")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from None
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_membership(
    db: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> WorkspaceMember | None:
    return await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )


async def require_member_workspace(
    workspace_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    membership = await get_membership(db, user.id, workspace_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return workspace


async def require_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Document:
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    membership = await get_membership(db, user.id, document.workspace_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return document


async def require_document_read(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Document:
    """Allow reading a document if the user is a member OR the document is public."""
    document = await db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not document.is_public:
        membership = await get_membership(db, user.id, document.workspace_id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return document


async def require_folder(
    folder_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Folder:
    folder = await db.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    membership = await get_membership(db, user.id, folder.workspace_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return folder


async def require_tag(
    tag_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Tag:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    membership = await get_membership(db, user.id, tag.workspace_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
    return tag


async def require_system_admin(user: CurrentUser) -> User:
    if not user.is_system_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System admin required")
    return user


ROLE_LEVELS: dict[Role, int] = {
    Role.owner: 4,
    Role.admin: 3,
    Role.manager: 2,
    Role.employee: 1,
}


def require_workspace_role(min_role: Role) -> Callable[..., Awaitable[Workspace]]:
    """Build a dependency requiring at least ``min_role`` in the target workspace.

    System admins bypass the membership/role check on any workspace.
    """

    async def _dep(workspace_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Workspace:
        workspace = await db.get(Workspace, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        if user.is_system_admin:
            return workspace
        membership = await get_membership(db, user.id, workspace_id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        if ROLE_LEVELS[Role(membership.role)] < ROLE_LEVELS[min_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires role: {min_role.value}")
        return workspace

    return _dep


def require_document_role(min_role: Role) -> Callable[..., Awaitable[Document]]:
    """Build a dependency requiring at least ``min_role`` in the document's workspace."""

    async def _dep(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Document:
        document = await db.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if user.is_system_admin:
            return document
        membership = await get_membership(db, user.id, document.workspace_id)
        if membership is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this workspace")
        if ROLE_LEVELS[Role(membership.role)] < ROLE_LEVELS[min_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires role: {min_role.value}")
        return document

    return _dep


DbSession = Annotated[AsyncSession, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
CurrentUser = Annotated[User, Depends(get_current_user)]
MemberWorkspace = Annotated[Workspace, Depends(require_member_workspace)]
DocumentResource = Annotated[Document, Depends(require_document)]
DocumentReadResource = Annotated[Document, Depends(require_document_read)]
DocumentManageResource = Annotated[Document, Depends(require_document_role(Role.manager))]
WorkspaceManagerRequired = Annotated[Workspace, Depends(require_workspace_role(Role.manager))]
WorkspaceAdminRequired = Annotated[Workspace, Depends(require_workspace_role(Role.admin))]
Storage = Annotated[StorageBackend, Depends(get_storage)]
FolderResource = Annotated[Folder, Depends(require_folder)]
TagResource = Annotated[Tag, Depends(require_tag)]
SystemAdmin = Annotated[User, Depends(require_system_admin)]
