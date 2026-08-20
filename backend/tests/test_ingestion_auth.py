import pytest

pytestmark = pytest.mark.asyncio


async def _register_project_with_key(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "ingest-auth@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Ingest Test"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    return project_id, key_res.json()["key"], key_res.json()["id"]


async def test_valid_api_key_can_start_a_trace(api_client):
    _project_id, full_key, _key_id = await _register_project_with_key(api_client)
    res = await api_client.post(
        "/api/v1/traces", json={"name": "run"}, headers={"Authorization": f"Bearer {full_key}"}
    )
    assert res.status_code == 200


async def test_missing_authorization_header_is_rejected(api_client):
    res = await api_client.post("/api/v1/traces", json={"name": "run"})
    assert res.status_code == 401


async def test_wrong_key_is_rejected(api_client):
    await _register_project_with_key(api_client)
    res = await api_client.post(
        "/api/v1/traces",
        json={"name": "run"},
        headers={"Authorization": "Bearer tw_totally-made-up"},
    )
    assert res.status_code == 401


async def test_revoked_key_is_rejected(api_client):
    project_id, full_key, key_id = await _register_project_with_key(api_client)
    await api_client.delete(f"/api/projects/{project_id}/api-keys/{key_id}")
    res = await api_client.post(
        "/api/v1/traces", json={"name": "run"}, headers={"Authorization": f"Bearer {full_key}"}
    )
    assert res.status_code == 401
