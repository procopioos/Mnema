from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.storage import LocalStorage
from app.models.document import Document, DocumentChunk, DocumentPage
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from tests.conftest import RegisterCallable
from tests.test_documents import _auth, _register_and_workspace, _upload


def _storage_paths() -> list[Path]:
    base_dir = LocalStorage(Path(get_settings().storage_dir)).base_dir
    return [p for p in base_dir.rglob("*") if p.is_file()]


async def _count(db: AsyncSession, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0


async def test_reset_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/admin/reset")
    assert response.status_code == 401


async def test_reset_requires_system_admin(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    data = await register_user(email="bob@example.com", full_name="Bob Example")
    response = await client.post("/api/v1/admin/reset", headers=_auth(data["access_token"]))
    assert response.status_code == 403


async def test_reset_clears_everything(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    await _upload(client, user["access_token"], workspace["id"])

    assert await _count(db_session, User) == 1
    assert await _count(db_session, Workspace) == 1
    assert await _count(db_session, WorkspaceMember) == 1
    assert await _count(db_session, Document) == 1
    assert await _count(db_session, DocumentChunk) == 0

    assert _storage_paths(), "expected a stored upload file"

    response = await client.post("/api/v1/admin/reset", headers=_auth(user["access_token"]))
    assert response.status_code == 204

    assert await _count(db_session, User) == 0
    assert await _count(db_session, Workspace) == 0
    assert await _count(db_session, WorkspaceMember) == 0
    assert await _count(db_session, Document) == 0
    assert await _count(db_session, DocumentPage) == 0
    assert not _storage_paths(), "storage should be empty after reset"
