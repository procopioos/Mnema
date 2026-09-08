from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import RegisterCallable
from tests.test_documents import _auth, _make_pdf, _register_and_workspace, _upload


async def _set_quota(
    client: AsyncClient,
    token: str,
    workspace_id: str,
    *,
    max_documents: int | None = None,
    max_storage_bytes: int | None = None,
) -> None:
    payload: dict = {}
    if max_documents is not None:
        payload["max_documents"] = max_documents
    if max_storage_bytes is not None:
        payload["max_storage_bytes"] = max_storage_bytes
    response = await client.patch(
        f"/api/v1/admin/workspaces/{workspace_id}",
        headers=_auth(token),
        json=payload,
    )
    assert response.status_code == 200, response.text


async def _raw_upload(
    client: AsyncClient,
    token: str,
    workspace_id: str,
    content: bytes,
) -> object:
    files = {"file": ("q.pdf", content, "application/pdf")}
    return await client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        headers=_auth(token),
        files=files,
    )


async def test_document_count_cap_blocks_then_unblocks(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    await _set_quota(client, user["access_token"], workspace["id"], max_documents=1)

    await _upload(client, user["access_token"], workspace["id"])

    overflow = await _raw_upload(client, user["access_token"], workspace["id"], _make_pdf())
    assert overflow.status_code == 413
    assert overflow.json()["detail"] == "documents_count_exceeded"

    listed = (
        await client.get(
            f"/api/v1/workspaces/{workspace['id']}/documents",
            headers=_auth(user["access_token"]),
        )
    ).json()
    doc = listed["items"][0]
    assert (
        await client.delete(f"/api/v1/documents/{doc['id']}", headers=_auth(user["access_token"]))
    ).status_code == 204

    await _upload(client, user["access_token"], workspace["id"])


async def test_storage_cap_blocks_then_lift_restores(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    await _set_quota(client, user["access_token"], workspace["id"], max_storage_bytes=300)

    overflow = await _raw_upload(client, user["access_token"], workspace["id"], _make_pdf())
    assert overflow.status_code == 413
    assert overflow.json()["detail"] == "storage_exceeded"

    await _set_quota(client, user["access_token"], workspace["id"], max_storage_bytes=50 * 1024 * 1024)
    await _upload(client, user["access_token"], workspace["id"])


async def test_null_columns_use_config_defaults(
    client: AsyncClient,
    register_user: RegisterCallable,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "max_documents_per_workspace", 1)

    user, workspace = await _register_and_workspace(client, register_user)
    await _upload(client, user["access_token"], workspace["id"])

    overflow = await _raw_upload(client, user["access_token"], workspace["id"], _make_pdf())
    assert overflow.status_code == 413
    assert overflow.json()["detail"] == "documents_count_exceeded"


async def test_workspace_payload_exposes_quota_and_usage(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    await _set_quota(
        client,
        user["access_token"],
        workspace["id"],
        max_documents=5,
        max_storage_bytes=50 * 1024 * 1024,
    )
    assert workspace["max_documents"] == 100  # config default before the admin override
    assert workspace["document_count"] == 0

    doc = await _upload(client, user["access_token"], workspace["id"])

    refreshed = (await client.get(f"/api/v1/workspaces/{workspace['id']}", headers=_auth(user["access_token"]))).json()
    assert refreshed["max_documents"] == 5
    assert refreshed["max_storage_bytes"] == 50 * 1024 * 1024
    assert refreshed["document_count"] == 1
    assert refreshed["storage_bytes"] == doc["size_bytes"]
    assert refreshed["role"] == "owner"


async def test_admin_stats_reports_workspace_usage(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    user, workspace = await _register_and_workspace(client, register_user)
    doc = await _upload(client, user["access_token"], workspace["id"])

    stats = (await client.get("/api/v1/admin/stats", headers=_auth(user["access_token"]))).json()
    row = next(entry for entry in stats["workspaces_usage"] if entry["id"] == workspace["id"])
    assert row["document_count"] == 1
    assert row["storage_bytes"] == doc["size_bytes"]
    assert row["member_count"] == 1
    assert row["max_documents"] is None  # raw override column, unset
    assert row["max_storage_bytes"] is None
