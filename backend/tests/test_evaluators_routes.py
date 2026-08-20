import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_create_project(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "evals@example.com", "password": "hunter2222"}
    )
    res = await api_client.post("/api/projects", json={"name": "Eval Project"})
    return res.json()["id"]


async def test_create_and_list_evaluator(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(
        f"/api/projects/{project_id}/evaluators",
        json={"name": "Groundedness", "judge_prompt_template": "Is the answer grounded?"},
    )
    assert create_res.status_code == 200
    body = create_res.json()
    assert body["name"] == "Groundedness"
    assert body["active"] is True
    assert body["score_scale"] == "1-5"

    list_res = await api_client.get(f"/api/projects/{project_id}/evaluators")
    assert len(list_res.json()) == 1


async def test_patch_evaluator_can_deactivate_it(api_client):
    project_id = await _register_and_create_project(api_client)
    create_res = await api_client.post(
        f"/api/projects/{project_id}/evaluators",
        json={"name": "Relevance", "judge_prompt_template": "Is it relevant?"},
    )
    evaluator_id = create_res.json()["id"]

    patch_res = await api_client.patch(
        f"/api/projects/{project_id}/evaluators/{evaluator_id}", json={"active": False}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["active"] is False
