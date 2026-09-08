import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditLog
from app.models.document import Document
from app.models.user import User

logger = logging.getLogger(__name__)


async def record(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    action: AuditAction,
    workspace_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """Persist a best-effort audit write; a failure never raises."""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                workspace_id=workspace_id,
                document_id=document_id,
                action=action,
                detail=detail,
                ip=ip,
            )
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to record audit log action=%s", action)


async def list_audit_logs(
    db: AsyncSession,
    workspace_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[tuple[AuditLog, str | None, str | None, str | None]], int]:
    """Return (audit row, user email, user full name, document filename) newest-first."""
    stmt = (
        select(AuditLog, User.email, User.full_name, Document.filename)
        .outerjoin(User, User.id == AuditLog.user_id)
        .outerjoin(Document, Document.id == AuditLog.document_id)
    )
    count_stmt = select(func.count()).select_from(AuditLog)
    if workspace_id is not None:
        stmt = stmt.where(AuditLog.workspace_id == workspace_id)
        count_stmt = count_stmt.where(AuditLog.workspace_id == workspace_id)
    total = await db.scalar(count_stmt) or 0
    result = await db.execute(stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit))
    return [(row, email, full_name, filename) for row, email, full_name, filename in result.all()], total
