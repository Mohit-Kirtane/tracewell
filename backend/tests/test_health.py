import pytest

pytestmark = pytest.mark.asyncio


async def test_health(api_client):
    res = await api_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
