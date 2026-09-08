import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion.pipeline import ingest_document
from tests.conftest import RegisterCallable
from tests.test_documents import _auth, _make_pdf, _register_and_workspace, _upload


async def _register_user_with_workspace(
    client: AsyncClient,
    register_user: RegisterCallable,
    email: str,
) -> tuple[dict, dict]:
    data = await register_user(email=email, full_name=email.split("@")[0].capitalize())
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()
    return data, workspaces[0]


async def test_private_document_hidden_from_other_workspaces(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    doc = await _upload(client, alice["access_token"], alice_ws["id"])

    carol, _ = await _register_user_with_workspace(client, register_user, "carol@example.com")

    assert doc["is_public"] is False
    response = await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(carol["access_token"]))
    assert response.status_code == 403

    public_list = (await client.get("/api/v1/documents/public", headers=_auth(carol["access_token"]))).json()
    assert public_list["total"] == 0


async def test_public_document_readable_across_workspaces(
    client: AsyncClient,
    register_user: RegisterCallable,
    db_session: AsyncSession,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    content = _make_pdf()
    doc = await _upload(client, alice["access_token"], alice_ws["id"], content=content)
    await ingest_document(db_session, uuid.UUID(doc["id"]))

    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    bob_ws = (await client.get("/api/v1/workspaces", headers=_auth(bob["access_token"]))).json()[0]

    # bob cannot read until alice makes the document public
    assert (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))).status_code == 403

    toggled = (
        await client.patch(
            f"/api/v1/documents/{doc['id']}/visibility",
            headers=_auth(alice["access_token"]),
            json={"is_public": True},
        )
    ).json()
    assert toggled["is_public"] is True

    updated = (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))).json()
    assert updated["status"] == "ready"
    assert updated["is_public"] is True

    pages = (await client.get(f"/api/v1/documents/{doc['id']}/pages", headers=_auth(bob["access_token"]))).json()
    assert len(pages) == 2
    assert "Employee Handbook" in pages[0]["content"]

    file_response = await client.get(f"/api/v1/documents/{doc['id']}/file", headers=_auth(bob["access_token"]))
    assert file_response.status_code == 200
    assert file_response.content == content

    # bob's own workspace is irrelevant to uploader_id — but verify public id is stable
    assert bob_ws["id"] != alice_ws["id"]


async def test_non_member_cannot_modify_public_document(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    doc = await _upload(client, alice["access_token"], alice_ws["id"])
    await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=_auth(alice["access_token"]),
        json={"is_public": True},
    )

    bob = await register_user(email="bob@example.com", full_name="Bob Example")

    toggle = await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=_auth(bob["access_token"]),
        json={"is_public": False},
    )
    assert toggle.status_code == 403

    delete = await client.delete(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))
    assert delete.status_code == 403


async def test_upload_with_is_public_flag(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    response = await client.post(
        f"/api/v1/workspaces/{alice_ws['id']}/documents",
        headers=_auth(alice["access_token"]),
        files={"file": ("handbook.pdf", _make_pdf(), "application/pdf")},
        data={"is_public": "true"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["is_public"] is True

    carol, _ = await _register_user_with_workspace(client, register_user, "carol@example.com")
    assert (
        await client.get(f"/api/v1/documents/{response.json()['id']}", headers=_auth(carol["access_token"]))
    ).status_code == 200


async def test_public_list_includes_workspace_name_and_excludes_private(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    public_doc = await _upload(client, alice["access_token"], alice_ws["id"])
    await client.patch(
        f"/api/v1/documents/{public_doc['id']}/visibility",
        headers=_auth(alice["access_token"]),
        json={"is_public": True},
    )
    private_doc = await _upload(client, alice["access_token"], alice_ws["id"], name="private.pdf")

    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    listing = (await client.get("/api/v1/documents/public", headers=_auth(bob["access_token"]))).json()

    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["id"] == public_doc["id"]
    assert item["workspace_name"] == alice_ws["name"]
    assert all(i["id"] != private_doc["id"] for i in listing["items"])

    paginated = (
        await client.get("/api/v1/documents/public?limit=5&offset=0", headers=_auth(bob["access_token"]))
    ).json()
    assert paginated["total"] == 1


async def test_visibility_toggle_then_private_again(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    doc = await _upload(client, alice["access_token"], alice_ws["id"])
    bob = await register_user(email="bob@example.com", full_name="Bob Example")

    await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=_auth(alice["access_token"]),
        json={"is_public": True},
    )
    assert (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))).status_code == 200

    await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=_auth(alice["access_token"]),
        json={"is_public": False},
    )
    assert (await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(bob["access_token"]))).status_code == 403
