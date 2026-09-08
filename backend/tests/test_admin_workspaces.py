import uuid

from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _admin_and_member(client: AsyncClient, register_user: RegisterCallable) -> tuple[dict, dict]:
    root = await register_user()
    member = await register_user(email="bob@example.com", full_name="Bob Example")
    return root, member


async def test_admin_lists_workspaces_with_metrics(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, _ = await _admin_and_member(client, register_user)
    response = await client.get("/api/v1/admin/workspaces", headers=_auth(root["access_token"]))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    for ws in body:
        assert ws["name"]
        assert ws["member_count"] == 1
        assert ws["storage_bytes"] == 0


async def test_regular_user_cannot_list_workspaces(client: AsyncClient, register_user: RegisterCallable) -> None:
    _, member = await _admin_and_member(client, register_user)
    response = await client.get("/api/v1/admin/workspaces", headers=_auth(member["access_token"]))
    assert response.status_code == 403


async def test_admin_creates_workspace(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, _ = await _admin_and_member(client, register_user)
    response = await client.post(
        "/api/v1/admin/workspaces",
        headers=_auth(root["access_token"]),
        json={"name": "Acme Consulting"},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Acme Consulting"
    assert created["slug"] == "acme-consulting"
    assert created["owner_id"] == root["user"]["id"]
    assert created["member_count"] == 1


async def test_admin_creates_workspace_with_specified_owner(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root, member = await _admin_and_member(client, register_user)
    response = await client.post(
        "/api/v1/admin/workspaces",
        headers=_auth(root["access_token"]),
        json={"name": "Bob's Team", "owner_id": member["user"]["id"]},
    )
    assert response.status_code == 201
    assert response.json()["owner_id"] == member["user"]["id"]


async def test_admin_renames_workspace(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, _ = await _admin_and_member(client, register_user)
    created = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Old Name"},
        )
    ).json()
    response = await client.patch(
        f"/api/v1/admin/workspaces/{created['id']}",
        headers=_auth(root["access_token"]),
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    renamed = response.json()
    assert renamed["name"] == "New Name"
    assert renamed["slug"] == "new-name"


async def test_admin_deletes_workspace(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, _ = await _admin_and_member(client, register_user)
    created = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Temp"},
        )
    ).json()
    response = await client.delete(
        f"/api/v1/admin/workspaces/{created['id']}",
        headers=_auth(root["access_token"]),
    )
    assert response.status_code == 204

    gone = await client.get("/api/v1/admin/workspaces", headers=_auth(root["access_token"]))
    assert all(ws["name"] != "Temp" for ws in gone.json())


async def test_delete_nonexistent_workspace_not_found(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root, _ = await _admin_and_member(client, register_user)
    response = await client.delete(
        f"/api/v1/admin/workspaces/{uuid.uuid4()}",
        headers=_auth(root["access_token"]),
    )
    assert response.status_code == 404


async def test_add_and_list_members(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, member = await _admin_and_member(client, register_user)
    created = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Team"},
        )
    ).json()

    response = await client.post(
        f"/api/v1/admin/workspaces/{created['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "manager"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "manager"

    listed = await client.get(
        f"/api/v1/admin/workspaces/{created['id']}/members",
        headers=_auth(root["access_token"]),
    )
    assert listed.status_code == 200
    emails = {m["email"] for m in listed.json()}
    assert emails == {root["user"]["email"], member["user"]["email"]}


async def test_update_member_role(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, member = await _admin_and_member(client, register_user)
    created = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Team"},
        )
    ).json()
    await client.post(
        f"/api/v1/admin/workspaces/{created['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "employee"},
    )
    response = await client.patch(
        f"/api/v1/admin/workspaces/{created['id']}/members/{member['user']['id']}",
        headers=_auth(root["access_token"]),
        json={"role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_cannot_change_owner_role_or_remove_owner(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root, _ = await _admin_and_member(client, register_user)
    created_ws = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Team"},
        )
    ).json()
    owner_id = created_ws["owner_id"]

    demote = await client.patch(
        f"/api/v1/admin/workspaces/{created_ws['id']}/members/{owner_id}",
        headers=_auth(root["access_token"]),
        json={"role": "employee"},
    )
    assert demote.status_code == 400

    remove = await client.delete(
        f"/api/v1/admin/workspaces/{created_ws['id']}/members/{owner_id}",
        headers=_auth(root["access_token"]),
    )
    assert remove.status_code == 400


async def test_remove_member(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, member = await _admin_and_member(client, register_user)
    created = (
        await client.post(
            "/api/v1/admin/workspaces",
            headers=_auth(root["access_token"]),
            json={"name": "Team"},
        )
    ).json()
    await client.post(
        f"/api/v1/admin/workspaces/{created['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "employee"},
    )
    response = await client.delete(
        f"/api/v1/admin/workspaces/{created['id']}/members/{member['user']['id']}",
        headers=_auth(root["access_token"]),
    )
    assert response.status_code == 204

    listed = await client.get(
        f"/api/v1/admin/workspaces/{created['id']}/members",
        headers=_auth(root["access_token"]),
    )
    assert all(m["user_id"] != member["user"]["id"] for m in listed.json())
