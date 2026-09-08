from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction
from app.services import audit as audit_service
from tests.conftest import RegisterCallable
from tests.test_documents import _auth, _make_pdf, _register_and_workspace, _upload


async def _list_audit(
    client: AsyncClient,
    token: str,
    workspace_id: str,
    *,
    endpoint: str | None = None,
    params: dict | None = None,
) -> dict:
    url = endpoint or f"/api/v1/workspaces/{workspace_id}/audit"
    response = await client.get(url, headers=_auth(token), params=params or {})
    assert response.status_code == 200, response.text
    return response.json()


async def test_login_is_logged(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    data = await register_user()
    login = await client.post("/api/v1/auth/login", json={"email": data["user"]["email"], "password": "password123"})
    assert login.status_code == 200

    workspace_id = (await client.get("/api/v1/workspaces", headers=_auth(data["access_token"]))).json()[0]["id"]
    audit = await _list_audit(client, data["access_token"], workspace_id)
    assert audit["total"] >= 1
    assert any(item["action"] == AuditAction.auth_login.value for item in audit["items"])
    login_row = next(item for item in audit["items"] if item["action"] == AuditAction.auth_login.value)
    assert login_row["user_email"] == data["user"]["email"]
    assert login_row["workspace_id"] == workspace_id
    assert login_row["document_id"] is None


async def test_document_events_are_logged(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(client, user["access_token"], workspace["id"])

    await client.get(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))
    await client.get(f"/api/v1/documents/{doc['id']}/file", headers=_auth(user["access_token"]))
    await client.get(f"/api/v1/documents/{doc['id']}/file", headers=_auth(user["access_token"]))
    await client.patch(
        f"/api/v1/documents/{doc['id']}/visibility",
        headers=_auth(user["access_token"]),
        json={"is_public": True},
    )

    audit = await _list_audit(client, user["access_token"], workspace["id"])

    def count(action: str) -> int:
        return len([item for item in audit["items"] if item["action"] == action])

    assert count(AuditAction.document_upload.value) == 1
    assert count(AuditAction.document_view.value) == 1
    assert count(AuditAction.document_download.value) == 2
    assert count(AuditAction.document_visibility.value) == 1

    upload_row = next(item for item in audit["items"] if item["action"] == AuditAction.document_upload.value)
    assert upload_row["document_id"] == doc["id"]
    assert upload_row["document_filename"] == "handbook.pdf"
    assert upload_row["detail"]["filename"] == "handbook.pdf"
    assert upload_row["user_email"] == user["user"]["email"]

    visibility_row = next(item for item in audit["items"] if item["action"] == AuditAction.document_visibility.value)
    assert visibility_row["detail"]["is_public"] is True

    await client.delete(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))

    audit_after = await _list_audit(client, user["access_token"], workspace["id"])
    delete_rows = [item for item in audit_after["items"] if item["action"] == AuditAction.document_delete.value]
    assert len(delete_rows) == 1
    assert delete_rows[0]["detail"]["filename"] == "handbook.pdf"
    assert delete_rows[0]["document_id"] is None


async def test_member_operations_are_logged(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    bob = await register_user(email="bob@example.com", full_name="Bob Example")

    add = await client.post(
        f"/api/v1/workspaces/{alice_ws['id']}/members",
        headers=_auth(alice["access_token"]),
        json={"user_id": bob["user"]["id"], "role": "employee"},
    )
    assert add.status_code == 201

    role = await client.patch(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{bob['user']['id']}",
        headers=_auth(alice["access_token"]),
        json={"role": "manager"},
    )
    assert role.status_code == 200

    removed = await client.delete(
        f"/api/v1/workspaces/{alice_ws['id']}/members/{bob['user']['id']}",
        headers=_auth(alice["access_token"]),
    )
    assert removed.status_code == 204

    audit = await _list_audit(client, alice["access_token"], alice_ws["id"])
    actions = [item["action"] for item in audit["items"]]
    assert AuditAction.workspace_member_add.value in actions
    assert AuditAction.workspace_member_role.value in actions
    assert AuditAction.workspace_member_remove.value in actions

    role_row = next(item for item in audit["items"] if item["action"] == AuditAction.workspace_member_role.value)
    assert role_row["detail"]["from"] == "employee"
    assert role_row["detail"]["to"] == "manager"
    assert role_row["detail"]["user_id"] == bob["user"]["id"]


async def test_employee_cannot_list_audit(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    bob = await register_user(email="bob@example.com", full_name="Bob Example")
    assert (
        await client.post(
            f"/api/v1/admin/workspaces/{alice_ws['id']}/members",
            headers=_auth(alice["access_token"]),
            json={"user_id": bob["user"]["id"], "role": "employee"},
        )
    ).status_code == 201

    response = await client.get(f"/api/v1/workspaces/{alice_ws['id']}/audit", headers=_auth(bob["access_token"]))
    assert response.status_code == 403


async def test_admin_audit_endpoint_filters_by_workspace(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    alice, alice_ws = await _register_and_workspace(client, register_user)
    other_ws = (
        await client.post(
            "/api/v1/workspaces",
            headers=_auth(alice["access_token"]),
            json={"name": "Second Space"},
        )
    ).json()

    await _upload(client, alice["access_token"], alice_ws["id"])

    all_rows = await _list_audit(client, alice["access_token"], alice_ws["id"], endpoint="/api/v1/admin/audit")
    assert all_rows["total"] >= 1
    assert any(item["workspace_id"] == other_ws["id"] for item in all_rows["items"])

    filtered = await _list_audit(
        client,
        alice["access_token"],
        alice_ws["id"],
        endpoint="/api/v1/admin/audit",
        params={"workspace_id": other_ws["id"]},
    )
    assert filtered["total"] >= 1
    assert all(item["workspace_id"] == other_ws["id"] for item in filtered["items"])


async def test_workspace_audit_pagination(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    for _ in range(3):
        await _upload(client, user["access_token"], workspace["id"])

    page1 = await _list_audit(client, user["access_token"], workspace["id"], params={"limit": 2})
    assert page1["total"] >= 3
    assert len(page1["items"]) == 2
    assert page1["items"][0]["created_at"] >= page1["items"][1]["created_at"]

    page2 = await _list_audit(client, user["access_token"], workspace["id"], params={"limit": 2, "offset": 2})
    assert len(page2["items"]) == page1["total"] - 2


async def test_record_never_raises_on_commit_failure(db_session: AsyncSession) -> None:
    await db_session.close()
    await audit_service.record(db_session, None, AuditAction.auth_login)  # must not raise
    await audit_service.record(
        db_session,
        None,
        AuditAction.document_upload,
        detail={"broken": _make_pdf},
    )  # unserializable detail again must not raise


async def test_admin_workspace_creates_are_logged(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    data = await register_user()
    created = await client.post(
        "/api/v1/workspaces",
        headers=_auth(data["access_token"]),
        json={"name": "Brand New Space"},
    )
    assert created.status_code == 201
    audit = await _list_audit(client, data["access_token"], created.json()["id"])
    assert any(item["action"] == AuditAction.admin_workspace_create.value for item in audit["items"])
