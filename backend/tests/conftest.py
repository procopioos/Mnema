import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://mnema:mnema@localhost:5432/mnema_test"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["STORAGE_DIR"] = "data-test"

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401  # register all models on Base.metadata
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.infrastructure.storage import LocalStorage
from app.main import app

test_engine = create_async_engine(os.environ["DATABASE_URL"])
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

RegisterCallable = Callable[..., Awaitable[dict]]


async def _reset_schema() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _reset_storage() -> None:
    base = LocalStorage(Path(get_settings().storage_dir)).base_dir
    base.mkdir(parents=True, exist_ok=True)
    for item in base.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            for sub in item.rglob("*"):
                if sub.is_file():
                    sub.unlink()
            for sub in sorted(item.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if sub.is_dir():
                    try:
                        sub.rmdir()
                    except OSError:
                        pass
            try:
                item.rmdir()
            except OSError:
                pass


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    await _reset_schema()
    _reset_storage()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with TestSession() as session:
        yield session


@pytest.fixture
def register_user(client: AsyncClient) -> RegisterCallable:
    async def _register(
        email: str = "alice@example.com",
        password: str = "password123",
        full_name: str = "Alice Example",
    ) -> dict:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register
