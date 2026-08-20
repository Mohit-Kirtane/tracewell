import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.db import get_db
from app.main import app


@pytest.fixture
def fake_db():
    client = AsyncMongoMockClient()
    return client["tracewell_test"]


@pytest.fixture
def api_client(fake_db):
    async def _get_db_override():
        return fake_db

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()
