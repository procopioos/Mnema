"""First-run setup flow: empty app requires a root account, first register becomes admin."""

import pytest


async def _setup_status(client) -> dict:
    response = await client.get("/api/v1/setup")
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def registered(client, register_user):
    data = await register_user()
    return data


async def test_setup_required_on_empty_db(client) -> None:
    assert await _setup_status(client) == {"required": True}


async def test_setup_not_required_after_first_register(client, registered) -> None:
    assert registered["user"]["is_root"] is True
    assert registered["user"]["is_system_admin"] is True
    assert await _setup_status(client) == {"required": False}


async def test_first_register_gets_root_and_workspace(client, registered) -> None:
    assert registered["user"]["is_root"] is True
    assert registered["user"]["is_system_admin"] is True
    assert registered["workspace_id"] is not None


async def test_second_register_is_not_admin(client, registered, register_user) -> None:
    second = await register_user(email="bob@example.com", full_name="Bob Bobson")
    assert second["user"]["is_root"] is False
    assert second["user"]["is_system_admin"] is False
    assert second["workspace_id"] is not None
    assert second["workspace_id"] != registered["workspace_id"]
    assert await _setup_status(client) == {"required": False}


async def test_setup_status_never_leaks_user_data(client, registered) -> None:
    body = await _setup_status(client)
    assert set(body.keys()) == {"required"}
