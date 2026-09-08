from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.storage import StorageBackend
from app.models.document import Document
from app.models.user import User
from app.models.workspace import Workspace


async def reset_app(db: AsyncSession, storage: StorageBackend) -> None:
    """Delete every document, workspace, and user, and clear stored files.

    Deletion order respects foreign-key RESTRICT constraints: documents must go
    first (they reference workspaces and uploaders), then workspaces (referenced
    by their owner), then users.
    """
    await db.execute(delete(Document))
    await db.execute(delete(Workspace))
    await db.execute(delete(User))
    await storage.clear_all()
    await db.commit()
