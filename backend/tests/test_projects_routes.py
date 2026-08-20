import pytest

pytestmark = pytest.mark.asyncio


async def _register(api_client, email="proj-user@example.com"):
    await api_client.post("/api/auth/register", json={"email": email, "password": "hunter2222"})


async def test_create_project_requires_authentication(api_client):
    res = await api_client.post("/api/projects", json={"name": "My Agent"})
    assert res.status_code == 401


async def test_create_and_list_project(api_client):
    await _register(api_client)
    create_res = await api_client.post("/api/projects", json={"name": "My Agent"})
    assert create_res.status_code == 200
    assert create_res.json()["name"] == "My Agent"

    list_res = await api_client.get("/api/projects")
    assert list_res.status_code == 200
    names = [p["name"] for p in list_res.json()]
    assert names == ["My Agent"]


async def test_projects_are_scoped_to_the_owning_user(api_client):
    await _register(api_client, email="owner@example.com")
    await api_client.post("/api/projects", json={"name": "Owner's Project"})
    await api_client.post("/api/auth/logout")

    await _register(api_client, email="other@example.com")
    list_res = await api_client.get("/api/projects")
    assert list_res.json() == []
