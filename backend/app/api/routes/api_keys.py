from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.api_key_security import generate_api_key
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import ApiKeyCreateOut, ApiKeyOut

router = APIRouter(prefix="/projects/{project_id}/api-keys", tags=["api-keys"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_api_key_out(key: dict) -> ApiKeyOut:
    return ApiKeyOut(
        id=key["_id"], prefix=key["prefix"], created_at=key["created_at"], revoked_at=key["revoked_at"]
    )


@router.post("", response_model=ApiKeyCreateOut)
async def create_api_key(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ApiKeyCreateOut:
    await _get_owned_project(project_id, user, db)

    full_key, prefix, key_hash = generate_api_key()
    record = {
        "_id": new_id(),
        "project_id": project_id,
        "prefix": prefix,
        "key_hash": key_hash,
        "created_at": utcnow(),
        "revoked_at": None,
    }
    await db.api_keys.insert_one(record)
    return ApiKeyCreateOut(**_to_api_key_out(record).model_dump(), key=full_key)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[ApiKeyOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.api_keys.find({"project_id": project_id}).sort("created_at", -1)
    return [_to_api_key_out(k) async for k in cursor]


@router.delete("/{key_id}")
async def revoke_api_key(
    project_id: str,
    key_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    await _get_owned_project(project_id, user, db)
    result = await db.api_keys.update_one(
        {"_id": key_id, "project_id": project_id}, {"$set": {"revoked_at": utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"ok": True}
