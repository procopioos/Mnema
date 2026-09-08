import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.folder import DocumentFolder
from app.models.workspace import Role, WorkspaceMember
from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_and_workspace(client: AsyncClient, register_user: RegisterCallable) -> tuple[dict, dict]:
    data = await register_user()
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()
    return data, workspaces[0]


async def _add_member(db_session: AsyncSession, workspace_id: str, user_id: str) -> None:
    db_session.add(
        WorkspaceMember(
            workspace_id=uuid.UUID(workspace_id),
            user_id=uuid.UUID(user_id),
            role=Role.employee,
        )
    )
    await db_session.commit()


async def _upload(client: AsyncClient, token: str, workspace_id: str, name: str = "doc.pdf") -> dict:
    response = await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=_auth(token),
        files={"file": (name, b"%PDF-1.4 minimal", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------


async def test_create_and_list_folders_with_counts(client: AsyncClient, register_user: RegisterCallable) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])

    created = await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    assert created.status_code == 201, created.text
    folder = created.json()
    assert folder["name"] == "HR"
    assert folder["document_count"] == 0

    doc = await _upload(client, user["access_token"], workspace["id"])
    put = await client.put(
        f"/api/v1/documents/{doc['id']}/folders",
        headers=headers,
        json={"folder_ids": [folder["id"]]},
    )
    assert put.status_code == 200, put.text
    assert [f["name"] for f in put.json()["folders"]] == ["HR"]

    listed = (await client.get(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers)).json()
    assert len(listed) == 1
    assert listed[0]["document_count"] == 1


async def test_duplicate_folder_name_conflict(client: AsyncClient, register_user: RegisterCallable) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])
    response = await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    assert response.status_code == 201
    duplicate = await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    assert duplicate.status_code == 409


async def test_rename_folder(client: AsyncClient, register_user: RegisterCallable) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])
    folder = (
        await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    ).json()

    renamed = await client.patch(f"/api/v1/folders/{folder['id']}", headers=headers, json={"name": "People"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "People"

    other = await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "Legal"})
    conflict = await client.patch(f"/api/v1/folders/{folder['id']}", headers=headers, json={"name": "Legal"})
    assert conflict.status_code == 409
    assert other.status_code == 201


async def test_delete_folder_unfiles_documents(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])
    folder = (
        await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    ).json()
    doc = await _upload(client, user["access_token"], workspace["id"])
    await client.put(
        f"/api/v1/documents/{doc['id']}/folders",
        headers=headers,
        json={"folder_ids": [folder["id"]]},
    )

    deleted = await client.delete(f"/api/v1/folders/{folder['id']}", headers=headers)
    assert deleted.status_code == 204

    detail = (await client.get(f"/api/v1/documents/{doc['id']}", headers=headers)).json()
    assert detail["folders"] == []

    unfiled = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            params={"unfiled": True},
            headers=headers,
        )
    ).json()
    assert unfiled["total"] == 1


async def test_folder_filters(client: AsyncClient, register_user: RegisterCallable) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])
    hr = (
        await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    ).json()
    legal = (
        await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "Legal"})
    ).json()

    doc_a = await _upload(client, user["access_token"], workspace["id"], name="a.pdf")
    doc_b = await _upload(client, user["access_token"], workspace["id"], name="b.pdf")
    doc_c = await _upload(client, user["access_token"], workspace["id"], name="c.pdf")
    await client.put(f"/api/v1/documents/{doc_a['id']}/folders", headers=headers, json={"folder_ids": [hr["id"]]})
    await client.put(
        f"/api/v1/documents/{doc_b['id']}/folders",
        headers=headers,
        json={"folder_ids": [legal["id"], hr["id"]]},
    )

    by_hr = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            params={"folder_id": hr["id"]},
            headers=headers,
        )
    ).json()
    assert by_hr["total"] == 2
    assert {item["id"] for item in by_hr["items"]} == {doc_a["id"], doc_b["id"]}

    unfiled = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            params={"unfiled": "true"},
            headers=headers,
        )
    ).json()
    assert {item["id"] for item in unfiled["items"]} == {doc_c["id"]}


async def test_assign_folder_from_other_workspace_rejected(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])
    foreign = await register_user(email="bob@example.com", full_name="Bob Example")
    bob_workspaces = (await client.get("/api/v1/workspaces", headers=_auth(foreign["access_token"]))).json()
    foreign_folder = (
        await client.post(
            f"/api/v1/workspaces/{bob_workspaces[0]['id']}/folders",
            headers=_auth(foreign["access_token"]),
            json={"name": "Bob's Folder"},
        )
    ).json()

    doc = await _upload(client, alice["access_token"], alice_workspace["id"])
    response = await client.put(
        f"/api/v1/documents/{doc['id']}/folders",
        headers=alice_headers,
        json={"folder_ids": [foreign_folder["id"]]},
    )
    assert response.status_code == 400


async def test_folder_membership_required(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, alice_workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])
    bob = await register_user(email="bob@example.com", full_name="Bob Example")

    folder = (
        await client.post(
            f"/api/v1/workspaces/{alice_workspace['id']}/folders",
            headers=alice_headers,
            json={"name": "HR"},
        )
    ).json()
    assert (
        await client.get(f"/api/v1/workspaces/{alice_workspace['id']}/folders", headers=_auth(bob["access_token"]))
    ).status_code == 403
    assert (
        await client.delete(f"/api/v1/folders/{folder['id']}", headers=_auth(bob["access_token"]))
    ).status_code == 403
    assert (await client.delete(f"/api/v1/folders/{uuid.uuid4()}", headers=alice_headers)).status_code == 404


async def test_clear_document_folders(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    headers = _auth(user["access_token"])
    folder = (
        await client.post(f"/api/v1/workspaces/{workspace['id']}/folders", headers=headers, json={"name": "HR"})
    ).json()
    doc = await _upload(client, user["access_token"], workspace["id"])
    await client.put(f"/api/v1/documents/{doc['id']}/folders", headers=headers, json={"folder_ids": [folder["id"]]})
    cleared = await client.put(f"/api/v1/documents/{doc['id']}/folders", headers=headers, json={"folder_ids": []})
    assert cleared.status_code == 200
    assert cleared.json()["folders"] == []
    remaining = list(
        await db_session.scalars(select(DocumentFolder).where(DocumentFolder.document_id == uuid.UUID(doc["id"])))
    )
    assert remaining == []


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


async def test_create_global_and_personal_tags(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])

    global_tag = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=alice_headers,
        json={"name": "Urgent", "color": "#ef4444", "scope": "global"},
    )
    assert global_tag.status_code == 201, global_tag.text
    assert global_tag.json()["user_id"] is None

    personal = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=alice_headers,
        json={"name": "My Focus", "color": "#3b82f6", "scope": "user"},
    )
    assert personal.status_code == 201, personal.text
    assert personal.json()["user_id"] == alice["user"]["id"]

    visible = (await client.get(f"/api/v1/workspaces/{workspace['id']}/tags", headers=alice_headers)).json()
    assert {tag["name"] for tag in visible} == {"Urgent", "My Focus"}


async def test_personal_tags_hidden_from_other_members(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    await _add_member(db_session, workspace["id"], bob["user"]["id"])

    shared = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Shared", "color": "#22c55e", "scope": "global"},
        )
    ).json()
    private = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Private", "color": "#a855f7", "scope": "user"},
        )
    ).json()

    visible_for_bob = (
        await client.get(f"/api/v1/workspaces/{workspace['id']}/tags", headers=_auth(bob["access_token"]))
    ).json()
    assert [tag["name"] for tag in visible_for_bob] == ["Shared"]

    doc = await _upload(client, alice["access_token"], workspace["id"])
    await client.put(
        f"/api/v1/documents/{doc['id']}/tags",
        headers=alice_headers,
        json={"tag_ids": [shared["id"], private["id"]]},
    )
    detail_for_bob = (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))).json()
    assert [tag["name"] for tag in detail_for_bob["tags"]] == ["Shared"]


async def test_same_tag_name_allowed_across_scopes(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])

    first = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=alice_headers,
        json={"name": "Later", "scope": "user"},
    )
    second = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=alice_headers,
        json={"name": "Later", "scope": "global"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    duplicate = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=alice_headers,
        json={"name": "Later", "scope": "global"},
    )
    assert duplicate.status_code == 409


async def test_invalid_color_rejected(client: AsyncClient, register_user: RegisterCallable) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    response = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/tags",
        headers=_auth(user["access_token"]),
        json={"name": "Bad", "color": "red"},
    )
    assert response.status_code == 422


async def test_update_and_delete_tag_permissions(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    await _add_member(db_session, workspace["id"], bob["user"]["id"])
    bob_headers = _auth(bob["access_token"])

    personal = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Mine", "color": "#a855f7", "scope": "user"},
        )
    ).json()
    global_tag = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Shared", "color": "#22c55e", "scope": "global"},
        )
    ).json()

    # Alice updates her own tag.
    updated = await client.patch(f"/api/v1/tags/{personal['id']}", headers=alice_headers, json={"color": "#f97316"})
    assert updated.status_code == 200
    assert updated.json()["color"] == "#f97316"

    # Bob, a member, may manage global tags…
    renamed_by_bob = await client.patch(f"/api/v1/tags/{global_tag['id']}", headers=bob_headers, json={"name": "Team"})
    assert renamed_by_bob.status_code == 200
    assert renamed_by_bob.json()["name"] == "Team"

    # …but not Alice's personal tags.
    bob_rename = await client.patch(f"/api/v1/tags/{personal['id']}", headers=bob_headers, json={"name": "X"})
    assert bob_rename.status_code == 403
    assert (await client.delete(f"/api/v1/tags/{personal['id']}", headers=bob_headers)).status_code == 403

    deleted = await client.delete(f"/api/v1/tags/{personal['id']}", headers=alice_headers)
    assert deleted.status_code == 204
    remaining = (await client.get(f"/api/v1/workspaces/{workspace['id']}/tags", headers=alice_headers)).json()
    assert [tag["name"] for tag in remaining] == ["Team"]


async def test_assign_tags_and_visibility_on_documents(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])

    global_tag = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Shared", "color": "#22c55e", "scope": "global"},
        )
    ).json()
    personal = (
        await client.post(
            f"/api/v1/workspaces/{workspace['id']}/tags",
            headers=alice_headers,
            json={"name": "Mine", "color": "#a855f7", "scope": "user"},
        )
    ).json()

    doc = await _upload(client, alice["access_token"], workspace["id"])
    assigned = await client.put(
        f"/api/v1/documents/{doc['id']}/tags",
        headers=alice_headers,
        json={"tag_ids": [global_tag["id"], personal["id"]]},
    )
    assert assigned.status_code == 200, assigned.text
    assert {tag["name"] for tag in assigned.json()["tags"]} == {"Shared", "Mine"}

    detail = (await client.get(f"/api/v1/documents/{doc['id']}", headers=alice_headers)).json()
    assert {tag["name"] for tag in detail["tags"]} == {"Shared", "Mine"}

    filtered = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            params={"tag_id": global_tag["id"]},
            headers=alice_headers,
        )
    ).json()
    assert filtered["total"] == 1

    cleared = await client.put(f"/api/v1/documents/{doc['id']}/tags", headers=alice_headers, json={"tag_ids": []})
    assert cleared.status_code == 200
    assert cleared.json()["tags"] == []

    none_left = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            params={"tag_id": global_tag["id"]},
            headers=alice_headers,
        )
    ).json()
    assert none_left["total"] == 0


async def test_assign_unknown_or_foreign_tag_rejected(client: AsyncClient, register_user: RegisterCallable) -> None:
    alice, workspace = await _register_and_workspace(client, register_user)
    alice_headers = _auth(alice["access_token"])
    doc = await _upload(client, alice["access_token"], workspace["id"])

    missing = await client.put(
        f"/api/v1/documents/{doc['id']}/tags",
        headers=alice_headers,
        json={"tag_ids": [str(uuid.uuid4())]},
    )
    assert missing.status_code == 400

    bad_payload = await client.put(
        f"/api/v1/documents/{doc['id']}/tags",
        headers=alice_headers,
        json={"tag_ids": ["not-a-uuid"]},
    )
    assert bad_payload.status_code == 422
