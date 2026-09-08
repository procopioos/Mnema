from pathlib import Path

from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import RegisterCallable
from tests.test_documents import _auth, _make_pdf, _register_and_workspace, _upload


async def _role_setup(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> tuple[dict, dict, dict]:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    return alice, bob, alice_ws


async def _grant_role(
    client: AsyncClient,
    admin_token: str,
    workspace_id: str,
    user_id: str,
    role: str,
) -> None:
    response = await client.post(
        f"/api/v1/admin/workspaces/{workspace_id}/members",
        headers=_auth(admin_token),
        json={"user_id": user_id, "role": role},
    )
    assert response.status_code == 201, response.text


async def test_workspace_role_reflected_in_list(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "employee")

    bob_workspaces = (await client.get("/api/v1/workspaces", headers=_auth(bob["access_token"]))).json()
    roles = {ws["id"]: ws["role"] for ws in bob_workspaces}
    assert roles[alice_ws["id"]] == "employee"
    assert any(role == "owner" for role in roles.values())

    alice_ws_after = (
        await client.get(f"/api/v1/workspaces/{alice_ws['id']}", headers=_auth(alice["access_token"]))
    ).json()
    assert alice_ws_after["role"] == "owner"


async def test_employee_cannot_modify_document(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "employee")

    doc = await _upload(client, alice["access_token"], alice_ws["id"])
    folder = (
        await client.post(
            f"/api/v1/workspaces/{alice_ws['id']}/folders",
            headers=_auth(alice["access_token"]),
            json={"name": "Legal"},
        )
    ).json()
    tag = (
        await client.post(
            f"/api/v1/workspaces/{alice_ws['id']}/tags",
            headers=_auth(alice["access_token"]),
            json={"name": "Shared", "scope": "global"},
        )
    ).json()

    headers = _auth(bob["access_token"])
    assert (await client.delete(f"/api/v1/documents/{doc['id']}", headers=headers)).status_code == 403
    assert (
        await client.patch(
            f"/api/v1/documents/{doc['id']}/visibility",
            headers=headers,
            json={"is_public": True},
        )
    ).status_code == 403
    assert (
        await client.put(
            f"/api/v1/documents/{doc['id']}/folders",
            headers=headers,
            json={"folder_ids": [folder["id"]]},
        )
    ).status_code == 403
    assert (
        await client.put(
            f"/api/v1/documents/{doc['id']}/tags",
            headers=headers,
            json={"tag_ids": [tag["id"]]},
        )
    ).status_code == 403

    # ...but an employee can still read the document
    assert (await client.get(f"/api/v1/documents/{doc['id']}", headers=headers)).status_code == 200


async def test_employee_can_upload(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "employee")

    response = await client.post(
        f"/api/v1/workspaces/{alice_ws['id']}/documents",
        headers=_auth(bob["access_token"]),
        files={"file": ("notes.pdf", _make_pdf(), "application/pdf")},
    )
    assert response.status_code == 201


async def test_manager_can_modify_document(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "manager")

    doc = await _upload(client, alice["access_token"], alice_ws["id"])
    headers = _auth(bob["access_token"])

    toggled = await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=headers,
        json={"is_public": True},
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_public"] is True

    deleted = await client.delete(f"/api/v1/documents/{doc['id']}", headers=headers)
    assert deleted.status_code == 204


async def test_workspace_management_requires_admin(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "employee")

    headers = _auth(bob["access_token"])
    patch = await client.patch(
        f"/api/v1/workspaces/{alice_ws['id']}",
        headers=headers,
        json={"name": "Nope"},
    )
    assert patch.status_code == 403
    assert (await client.delete(f"/api/v1/workspaces/{alice_ws['id']}", headers=headers)).status_code == 403
    assert (await client.get(f"/api/v1/workspaces/{alice_ws['id']}/members", headers=headers)).status_code == 403


async def test_workspace_admin_manages_members(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "admin")

    carol = await register_user(email="carol@example.com", full_name="Carol Example")

    members = (
        await client.get(f"/api/v1/workspaces/{alice_ws['id']}/members", headers=_auth(bob["access_token"]))
    ).json()
    assert len(members) == 2

    added = await client.post(
        f"/api/v1/workspaces/{alice_ws['id']}/members",
        headers=_auth(bob["access_token"]),
        json={"user_id": carol["user"]["id"], "role": "employee"},
    )
    assert added.status_code == 201
    assert added.json()["role"] == "employee"

    promoted = await client.patch(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{carol['user']['id']}",
        headers=_auth(bob["access_token"]),
        json={"role": "manager"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "manager"

    removed = await client.delete(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{carol['user']['id']}",
        headers=_auth(bob["access_token"]),
    )
    assert removed.status_code == 204


async def test_owner_cannot_be_demoted(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, bob, alice_ws = await _role_setup(client, register_user)
    await _grant_role(client, alice["access_token"], alice_ws["id"], bob["user"]["id"], "admin")

    demote = await client.patch(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{alice['user']['id']}",
        headers=_auth(bob["access_token"]),
        json={"role": "employee"},
    )
    assert demote.status_code == 400

    remove = await client.delete(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{alice['user']['id']}",
        headers=_auth(bob["access_token"]),
    )
    assert remove.status_code == 400


async def test_owner_can_rename_and_delete_own_workspace(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    doc = await _upload(client, alice["access_token"], alice_ws["id"])
    headers = _auth(alice["access_token"])
    stored_file = Path(get_settings().storage_dir) / alice_ws["id"] / doc["id"] / doc["filename"]
    assert stored_file.is_file()

    renamed = await client.patch(
        f"/api/v1/workspaces/{alice_ws['id']}",
        headers=headers,
        json={"name": "Renamed Team"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed Team"
    assert renamed.json()["role"] == "owner"

    deleted = await client.delete(f"/api/v1/workspaces/{alice_ws['id']}", headers=headers)
    assert deleted.status_code == 204

    assert not stored_file.exists()
    assert (await client.get(f"/api/v1/workspaces/{alice_ws['id']}", headers=headers)).status_code == 404


async def test_system_admin_bypasses_workspace_role(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user()
    carol = await register_user(email="carol@example.com", full_name="Carol Example")
    carol_ws = (await client.get("/api/v1/workspaces", headers=_auth(carol["access_token"]))).json()[0]

    renamed = await client.patch(
        f"/api/v1/workspaces/{carol_ws['id']}",
        headers=_auth(root["access_token"]),
        json={"name": "Taken Over"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Taken Over"
