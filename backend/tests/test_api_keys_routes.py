import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_create_project(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "keys-user@example.com", "password": "hunter2222"}
    )
    res = await api_client.post("/api/projects", json={"name": "My Agent"})
    return res.json()["id"]


async def test_create_api_key_returns_full_key_once(api_client):
    project_id = await _register_and_create_project(api_client)
    res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["key"].startswith("tw_")
    assert body["prefix"] == body["key"][:11]


async def test_list_api_keys_never_returns_the_full_key(api_client):
    project_id = await _register_and_create_project(api_client)
    await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    res = await api_client.get(f"/api/projects/{project_id}/api-keys")
    assert res.status_code == 200
    assert "key" not in res.json()[0]
    assert "prefix" in res.json()[0]


async def test_revoke_api_key_sets_revoked_at(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    key_id = create_res.json()["id"]

    revoke_res = await api_client.delete(f"/api/projects/{project_id}/api-keys/{key_id}")
    assert revoke_res.status_code == 200

    list_res = await api_client.get(f"/api/projects/{project_id}/api-keys")
    assert list_res.json()[0]["revoked_at"] is not None


async def test_cannot_manage_api_keys_for_a_project_you_do_not_own(api_client):
    project_id = await _register_and_create_project(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "intruder@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    assert res.status_code == 404
