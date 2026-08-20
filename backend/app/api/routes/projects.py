from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_project_out(project: dict) -> ProjectOut:
    return ProjectOut(id=project["_id"], name=project["name"], created_at=project["created_at"])


@router.post("", response_model=ProjectOut)
async def create_project(
    payload: ProjectCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> ProjectOut:
    project = {
        "_id": new_id(),
        "user_id": user["_id"],
        "name": payload.name,
        "created_at": utcnow(),
    }
    await db.projects.insert_one(project)
    return _to_project_out(project)


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: dict = Depends(get_current_user), db: AsyncIOMotorDatabase = Depends(get_db)
) -> list[ProjectOut]:
    cursor = db.projects.find({"user_id": user["_id"]}).sort("created_at", -1)
    return [_to_project_out(p) async for p in cursor]
