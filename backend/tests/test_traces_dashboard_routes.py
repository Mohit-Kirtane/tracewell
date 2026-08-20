import pytest

pytestmark = pytest.mark.asyncio


async def _register_project_and_trace(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "dash@example.com", "password": "hunter2222"}
    )
    project_res = await api_client.post("/api/projects", json={"name": "Dash Project"})
    project_id = project_res.json()["id"]
    key_res = await api_client.post(f"/api/projects/{project_id}/api-keys", json={})
    headers = {"Authorization": f"Bearer {key_res.json()['key']}"}

    trace_res = await api_client.post("/api/v1/traces", json={"name": "run-1"}, headers=headers)
    trace_id = trace_res.json()["id"]
    span = {
        "id": "span-1",
        "parent_id": None,
        "type": "llm",
        "name": "gemini-call",
        "input": "hi",
        "output": "hello",
        "started_at": "2026-08-20T00:00:00Z",
        "ended_at": "2026-08-20T00:00:01Z",
        "tokens": 10,
        "error": None,
    }
    await api_client.patch(
        f"/api/v1/traces/{trace_id}",
        json={"status": "complete", "spans": [span]},
        headers=headers,
    )
    return project_id, trace_id


async def test_list_traces_for_a_project(api_client):
    project_id, _trace_id = await _register_project_and_trace(api_client)
    res = await api_client.get(f"/api/projects/{project_id}/traces")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["status"] == "complete"
    assert body[0]["total_tokens"] == 10
    assert body[0]["span_count"] == 1


async def test_get_trace_detail_includes_spans_and_empty_evaluations(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    res = await api_client.get(f"/api/traces/{trace_id}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["spans"]) == 1
    assert body["evaluations"] == []


async def test_cannot_view_traces_for_a_project_you_do_not_own(api_client):
    project_id, trace_id = await _register_project_and_trace(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "intruder-dash@example.com", "password": "hunter2222"}
    )

    list_res = await api_client.get(f"/api/projects/{project_id}/traces")
    assert list_res.status_code == 404

    detail_res = await api_client.get(f"/api/traces/{trace_id}")
    assert detail_res.status_code == 404


async def test_rescore_clears_existing_evaluations_for_the_trace(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    res = await api_client.post(f"/api/traces/{trace_id}/rescore")
    assert res.status_code == 200


async def test_rescore_requires_ownership(api_client):
    _project_id, trace_id = await _register_project_and_trace(api_client)
    await api_client.post("/api/auth/logout")
    await api_client.post(
        "/api/auth/register", json={"email": "rescore-intruder@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(f"/api/traces/{trace_id}/rescore")
    assert res.status_code == 404
