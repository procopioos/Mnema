from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_first_register_is_root_admin(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    assert data["user"]["is_system_admin"] is True
    assert data["user"]["is_root"] is True


async def test_second_register_is_not_admin(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    data = await register_user(email="bob@example.com", full_name="Bob Example")
    assert data["user"]["is_system_admin"] is False
    assert data["user"]["is_root"] is False


async def test_stats_requires_system_admin(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    data = await register_user(email="bob@example.com", full_name="Bob Example")
    response = await client.get("/api/v1/admin/stats", headers=_auth(data["access_token"]))
    assert response.status_code == 403


async def test_stats_returns_counts(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    await register_user(email="bob@example.com", full_name="Bob Example")
    response = await client.get("/api/v1/admin/stats", headers=_auth(data["access_token"]))
    assert response.status_code == 200
    body = response.json()
    assert body["users"] == 2
    assert body["workspaces"] == 2
    assert body["documents"]["total"] == 0
    assert body["storage_bytes"] == 0


async def test_admin_promotes_user(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    bob = await register_user(email="bob@example.com", full_name="Bob Example")

    response = await client.patch(
        f"/api/v1/admin/users/{bob['user']['id']}",
        headers=_auth(root["access_token"]),
        json={"is_system_admin": True},
    )
    assert response.status_code == 200
    assert response.json()["is_system_admin"] is True

    unauthorized = await client.get("/api/v1/admin/stats", headers=_auth(bob["access_token"]))
    assert unauthorized.status_code == 200


async def test_regular_cannot_promote(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    carol = await register_user(email="carol@example.com", full_name="Carol Example")

    response = await client.patch(
        f"/api/v1/admin/users/{carol['user']['id']}",
        headers=_auth(bob["access_token"]),
        json={"is_system_admin": True},
    )
    assert response.status_code == 403


async def test_root_cannot_be_demoted(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    response = await client.patch(
        f"/api/v1/admin/users/{root['user']['id']}",
        headers=_auth(root["access_token"]),
        json={"is_system_admin": False},
    )
    assert response.status_code == 403


async def test_other_admin_cannot_demote_root(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    promoted = await client.patch(
        f"/api/v1/admin/users/{bob['user']['id']}",
        headers=_auth(root["access_token"]),
        json={"is_system_admin": True},
    )
    assert promoted.status_code == 200

    response = await client.patch(
        f"/api/v1/admin/users/{root['user']['id']}",
        headers=_auth(bob["access_token"]),
        json={"is_system_admin": False},
    )
    assert response.status_code == 403


async def test_list_users_search(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    await register_user(email="bob@example.com", full_name="Bob Example")

    all_users = await client.get("/api/v1/admin/users", headers=_auth(root["access_token"]))
    assert all_users.status_code == 200
    assert len(all_users.json()) == 2

    by_email = await client.get("/api/v1/admin/users?q=bob", headers=_auth(root["access_token"]))
    assert by_email.status_code == 200
    assert len(by_email.json()) == 1
    assert by_email.json()[0]["email"] == "bob@example.com"
