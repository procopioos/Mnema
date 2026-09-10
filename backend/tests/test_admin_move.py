import uuid

from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_team_ws(client: AsyncClient, root_token: str, name: str = "Team") -> dict:
    response = await client.post(
        "/api/v1/admin/workspaces",
        headers=_auth(root_token),
        json={"name": name},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_move_member_removes_from_source_adds_to_target(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user()
    member = await register_user(email="bob@example.com", full_name="Bob Example")

    source = await _create_team_ws(client, root["access_token"], name="Source")
    target = await _create_team_ws(client, root["access_token"], name="Target")

    await client.post(
        f"/api/v1/admin/workspaces/{source['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "employee"},
    )

    response = await client.post(
        f"/api/v1/admin/users/{member['user']['id']}/move",
        headers=_auth(root["access_token"]),
        json={
            "from_workspace_id": source["id"],
            "to_workspace_id": target["id"],
            "role": "manager",
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"

    source_members = (
        await client.get(
            f"/api/v1/admin/workspaces/{source['id']}/members",
            headers=_auth(root["access_token"]),
        )
    ).json()
    assert all(m["user_id"] != member["user"]["id"] for m in source_members)

    target_members = (
        await client.get(
            f"/api/v1/admin/workspaces/{target['id']}/members",
            headers=_auth(root["access_token"]),
        )
    ).json()
    bob = next(m for m in target_members if m["user_id"] == member["user"]["id"])
    assert bob["role"] == "manager"


async def test_move_owner_blocked(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    created = await _create_team_ws(client, root["access_token"], name="Source")
    target = await _create_team_ws(client, root["access_token"], name="Target")
    owner_id = created["owner_id"]

    response = await client.post(
        f"/api/v1/admin/users/{owner_id}/move",
        headers=_auth(root["access_token"]),
        json={
            "from_workspace_id": created["id"],
            "to_workspace_id": target["id"],
            "role": "employee",
        },
    )
    assert response.status_code == 400


async def test_move_non_member_blocked(client: AsyncClient, register_user: RegisterCallable) -> None:
    root, member = await register_user(), await register_user(email="bob@example.com", full_name="Bob Example")
    source = await _create_team_ws(client, root["access_token"], name="Source")
    target = await _create_team_ws(client, root["access_token"], name="Target")

    response = await client.post(
        f"/api/v1/admin/users/{member['user']['id']}/move",
        headers=_auth(root["access_token"]),
        json={"from_workspace_id": source["id"], "to_workspace_id": target["id"], "role": "employee"},
    )
    assert response.status_code == 400


async def test_move_same_workspace_blocked(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    member = await register_user(email="bob@example.com", full_name="Bob Example")
    source = await _create_team_ws(client, root["access_token"], name="Source")
    await client.post(
        f"/api/v1/admin/workspaces/{source['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "employee"},
    )

    response = await client.post(
        f"/api/v1/admin/users/{member['user']['id']}/move",
        headers=_auth(root["access_token"]),
        json={"from_workspace_id": source["id"], "to_workspace_id": source["id"], "role": "employee"},
    )
    assert response.status_code == 400


async def test_move_requires_system_admin(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    member = await register_user(email="bob@example.com", full_name="Bob Example")
    source = await _create_team_ws(client, root["access_token"], name="Source")
    _ = await _create_team_ws(client, root["access_token"], name="Target")

    response = await client.post(
        f"/api/v1/admin/users/{member['user']['id']}/move",
        headers=_auth(member["access_token"]),
        json={
            "from_workspace_id": source["id"],
            "to_workspace_id": "00000000-0000-0000-0000-000000000002",
            "role": "employee",
        },
    )
    assert response.status_code == 403


async def test_move_logs_audit(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    member = await register_user(email="bob@example.com", full_name="Bob Example")
    source = await _create_team_ws(client, root["access_token"], name="Source")
    target = await _create_team_ws(client, root["access_token"], name="Target")
    await client.post(
        f"/api/v1/admin/workspaces/{source['id']}/members",
        headers=_auth(root["access_token"]),
        json={"user_id": member["user"]["id"], "role": "employee"},
    )

    await client.post(
        f"/api/v1/admin/users/{member['user']['id']}/move",
        headers=_auth(root["access_token"]),
        json={"from_workspace_id": source["id"], "to_workspace_id": target["id"], "role": "employee"},
    )

    audit = await client.get(
        f"/api/v1/admin/audit?workspace_id={target['id']}",
        headers=_auth(root["access_token"]),
    )
    assert audit.status_code == 200
    moves = [row for row in audit.json()["items"] if row["action"] == "workspace.member.move"]
    assert len(moves) == 1
    detail = moves[0]["detail"]
    assert detail["from_workspace_id"] == source["id"]
    assert detail["to_workspace_id"] == target["id"]


async def test_move_nonexistent_user_not_found(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    source = await _create_team_ws(client, root["access_token"], name="Source")
    target = await _create_team_ws(client, root["access_token"], name="Target")

    response = await client.post(
        f"/api/v1/admin/users/{uuid.uuid4()}/move",
        headers=_auth(root["access_token"]),
        json={"from_workspace_id": source["id"], "to_workspace_id": target["id"], "role": "employee"},
    )
    assert response.status_code == 404
