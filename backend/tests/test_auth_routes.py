import pytest

pytestmark = pytest.mark.asyncio


async def test_register_creates_user_and_sets_cookie(api_client):
    res = await api_client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "hunter2222"}
    )
    assert res.status_code == 200
    assert res.json()["email"] == "a@example.com"
    assert "access_token" in res.cookies


async def test_register_rejects_duplicate_email(api_client):
    payload = {"email": "dup@example.com", "password": "hunter2222"}
    await api_client.post("/api/auth/register", json=payload)
    res = await api_client.post("/api/auth/register", json=payload)
    assert res.status_code == 409


async def test_login_with_correct_password_succeeds(api_client):
    payload = {"email": "b@example.com", "password": "hunter2222"}
    await api_client.post("/api/auth/register", json=payload)
    res = await api_client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    assert "access_token" in res.cookies


async def test_login_with_wrong_password_fails(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "c@example.com", "password": "hunter2222"}
    )
    res = await api_client.post(
        "/api/auth/login", json={"email": "c@example.com", "password": "wrong-pass"}
    )
    assert res.status_code == 401


async def test_me_requires_authentication(api_client):
    res = await api_client.get("/api/auth/me")
    assert res.status_code == 401


async def test_me_returns_current_user_after_login(api_client):
    await api_client.post(
        "/api/auth/register", json={"email": "d@example.com", "password": "hunter2222"}
    )
    res = await api_client.get("/api/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == "d@example.com"
