from uuid import UUID

from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_register_creates_user_and_tokens(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    assert set(data) >= {"access_token", "refresh_token", "token_type", "user", "workspace_id"}
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["full_name"] == "Alice Example"
    assert UUID(data["workspace_id"])


async def test_register_workspace_id_matches_listed_workspace(
    client: AsyncClient, register_user: RegisterCallable
) -> None:
    data = await register_user()
    workspaces = await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))
    assert workspaces.status_code == 200
    assert workspaces.json()[0]["id"] == data["workspace_id"]


async def test_register_lowercases_email(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user(email="Alice@Example.COM")
    assert data["user"]["email"] == "alice@example.com"


async def test_register_duplicate_email_conflicts(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123", "full_name": "Alice Again"},
    )
    assert response.status_code == 409


async def test_register_short_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short", "full_name": "Short Pw"},
    )
    assert response.status_code == 422


async def test_login_success(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_returns_workspace_id(client: AsyncClient, register_user: RegisterCallable) -> None:
    registered = await register_user()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert UUID(response.json()["workspace_id"]) == UUID(registered["workspace_id"])


async def test_login_returns_own_workspace_with_multiple_users(
    client: AsyncClient, register_user: RegisterCallable
) -> None:
    alice = await register_user(email="alice@example.com", full_name="Alice Example")
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    assert alice["workspace_id"] != bob["workspace_id"]

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert UUID(response.json()["workspace_id"]) == UUID(bob["workspace_id"])


async def test_list_workspaces_only_returns_own(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice = await register_user(email="alice@example.com", full_name="Alice Example")
    await register_user(email="bob@example.com", full_name="Bob Example")

    workspaces = await client.get("/api/v1/workspaces", headers=_auth(alice["access_token"]))
    assert workspaces.status_code == 200
    assert [ws["id"] for ws in workspaces.json()] == [alice["workspace_id"]]


async def test_login_wrong_password(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_me_returns_current_user(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.get("/api/v1/auth/me", headers=_auth(data["access_token"]))
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_me_without_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_returns_new_access_token(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_access_token_not_accepted_as_refresh(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["access_token"]},
    )
    assert response.status_code == 401
