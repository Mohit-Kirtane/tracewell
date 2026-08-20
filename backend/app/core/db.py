from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongodb_db_name]


async def get_db() -> AsyncIOMotorDatabase:
    return get_database()
