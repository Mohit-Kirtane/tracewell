import pytest

pytestmark = pytest.mark.asyncio


async def _register_project_with_key(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "ingest@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Ingest Project"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    return project_id, {"Authorization": f"Bearer {key_res.json()['key']}"}


async def test_start_trace_returns_an_id(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    assert res.status_code == 200
    assert "id" in res.json()


async def test_patch_appends_spans_and_rolls_up_tokens(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    create_res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    trace_id = create_res.json()["id"]

    span = {
        "id": "span-1",
        "parent_id": None,
        "type": "llm",
        "name": "gemini-call",
        "input": "hello",
        "output": "hi there",
        "started_at": "2026-08-20T00:00:00Z",
        "ended_at": "2026-08-20T00:00:01Z",
        "tokens": 42,
        "error": None,
    }
    patch_res = await api_client.patch(
        f"/api/v1/traces/{trace_id}",
        json={"status": "complete", "spans": [span]},
        headers=headers,
    )
    assert patch_res.status_code == 200


async def test_cannot_patch_a_trace_belonging_to_another_project(api_client):
    _project_id, headers = await _register_project_with_key(api_client)
    create_res = await api_client.post("/api/v1/traces", json={"name": "test-run"}, headers=headers)
    trace_id = create_res.json()["id"]

    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "other-ingest@example.com", "password": "hunter2222"}
    )
    other_project_res = await api_client.post("/api/projects", json={"name": "Other"})
    other_key_res = await api_client.post(
        f"/api/projects/{other_project_res.json()['id']}/api-keys", json={}
    )
    other_headers = {"Authorization": f"Bearer {other_key_res.json()['key']}"}

    res = await api_client.patch(
        f"/api/v1/traces/{trace_id}", json={"status": "complete"}, headers=other_headers
    )
    assert res.status_code == 404
