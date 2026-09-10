from httpx import AsyncClient

from tests.conftest import RegisterCallable


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_with_code(
    client: AsyncClient,
    code: str | None,
    email: str,
    full_name: str,
) -> dict:
    payload = {"email": email, "password": "password123", "full_name": full_name}
    if code is not None:
        payload["workspace_code"] = code
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_with_code_joins_as_employee(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user(email="alice@example.com", full_name="Alice Example")
    code = (await client.get("/api/v1/workspaces", headers=_auth(root["access_token"]))).json()[0]["invite_code"]

    joined = await _register_with_code(client, code, "bob@example.com", "Bob Example")

    assert joined["workspace_id"] == root["workspace_id"]
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(joined["access_token"]))).json()
    assert len(workspaces) == 1
    assert workspaces[0]["id"] == root["workspace_id"]
    assert workspaces[0]["role"] == "employee"


async def test_register_with_invalid_code_rejected(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    await register_user()
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "password123",
            "full_name": "Bob Example",
            "workspace_code": "999999",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "invalid_invite_code"


async def test_register_with_non_digit_code_rejected(client: AsyncClient, register_user: RegisterCallable) -> None:
    await register_user()
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "password123",
            "full_name": "Bob Example",
            "workspace_code": " 123456  ",
        },
    )
    assert response.status_code == 422


async def test_register_without_code_creates_personal_workspace(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user()

    solo = await _register_with_code(client, None, "carol@example.com", "Carol Example")
    assert solo["workspace_id"] != root["workspace_id"]
    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(solo["access_token"]))).json()
    assert len(workspaces) == 1
    assert workspaces[0]["role"] == "owner"


async def test_workspaces_expose_unique_invite_codes(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user()
    _ = await _register_with_code(client, None, "carol@example.com", "Carol Example")

    workspaces = (await client.get("/api/v1/workspaces", headers=_auth(root["access_token"]))).json()
    codes = [ws["invite_code"] for ws in workspaces]
    assert all(code and len(code) == 6 and code.isdigit() for code in codes)
    assert len(set(codes)) == len(codes)


async def test_admin_regenerate_code_invalidates_old(
    client: AsyncClient,
    register_user: RegisterCallable,
) -> None:
    root = await register_user()
    admin_ws = (await client.get("/api/v1/admin/workspaces", headers=_auth(root["access_token"]))).json()
    ws = admin_ws[0]
    old_code = ws["invite_code"]

    response = await client.post(
        f"/api/v1/admin/workspaces/{ws['id']}/regenerate-code",
        headers=_auth(root["access_token"]),
    )
    assert response.status_code == 200
    new_code = response.json()["invite_code"]
    assert new_code != old_code

    old_rejected = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "password123",
            "full_name": "Bob Example",
            "workspace_code": old_code,
        },
    )
    assert old_rejected.status_code == 404

    accepted = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "bob@example.com",
            "password": "password123",
            "full_name": "Bob Example",
            "workspace_code": new_code,
        },
    )
    assert accepted.status_code == 201
    assert accepted.json()["workspace_id"] == ws["id"]


async def test_non_admin_cannot_regenerate_code(client: AsyncClient, register_user: RegisterCallable) -> None:
    root = await register_user()
    code = (await client.get("/api/v1/workspaces", headers=_auth(root["access_token"]))).json()[0]["invite_code"]
    joined = await _register_with_code(client, code, "bob@example.com", "Bob Example")
    ws_id = joined["workspace_id"]

    response = await client.post(
        f"/api/v1/admin/workspaces/{ws_id}/regenerate-code",
        headers=_auth(joined["access_token"]),
    )
    assert response.status_code == 403
