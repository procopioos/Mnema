import uuid

from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_register_creates_default_workspace(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Alice's Workspace"
    assert workspaces[0]["owner_id"] == data["user"]["id"]


async def test_create_workspace(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.post(
        "/api/v1/workspaces",
        headers=_auth(data["access_token"]),
        json={"name": "Acme Consulting"},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Acme Consulting"
    assert created["slug"] == "acme-consulting"
    assert created["owner_id"] == data["user"]["id"]


async def test_create_duplicate_slug_gets_unique(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    for _ in range(2):
        response = await client.post(
            "/api/v1/workspaces",
            headers=_auth(data["access_token"]),
            json={"name": "Acme"},
        )
        assert response.status_code == 201
    assert len((await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()) == 3


async def test_get_workspace_as_member(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()
    response = await client.get(f"/api/v1/workspaces/{workspaces[0]['id']}", headers=_auth(data["access_token"]))
    assert response.status_code == 200
    assert response.json()["id"] == workspaces[0]["id"]


async def test_get_foreign_workspace_forbidden(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice = await register_user()
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    alice_workspaces = (await client.get("/api/v1/workspaces", headers=_auth(alice["access_token"]))).json()
    foreign_id = alice_workspaces[0]["id"]

    response = await client.get(f"/api/v1/workspaces/{foreign_id}", headers=_auth(bob["access_token"]))
    assert response.status_code == 403


async def test_get_nonexistent_workspace_not_found(client: AsyncClient, register_user: RegisterCallable) -> None:
    data = await register_user()
    response = await client.get(f"/api/v1/workspaces/{uuid.uuid4()}", headers=_auth(data["access_token"]))
    assert response.status_code == 404
