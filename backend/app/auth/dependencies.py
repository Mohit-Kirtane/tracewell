from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.api_key_security import verify_api_key
from app.core.db import get_db
from app.core.security import COOKIE_NAME, decode_access_token


async def get_current_user(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    user_id = decode_access_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await db.users.find_one({"_id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_current_project(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    full_key = auth_header.removeprefix("Bearer ").strip()
    if len(full_key) < 11:
        raise HTTPException(status_code=401, detail="Invalid API key")

    prefix = full_key[:11]
    candidate = await db.api_keys.find_one({"prefix": prefix, "revoked_at": None})
    if candidate is None or not verify_api_key(full_key, candidate["key_hash"]):
        raise HTTPException(status_code=401, detail="Invalid API key")

    project = await db.projects.find_one({"_id": candidate["project_id"]})
    if project is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return project
