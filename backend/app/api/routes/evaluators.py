from fastapi import APIRouter, Body, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import EvaluatorCreate, EvaluatorOut

router = APIRouter(prefix="/projects/{project_id}/evaluators", tags=["evaluators"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_evaluator_out(evaluator: dict) -> EvaluatorOut:
    return EvaluatorOut(
        id=evaluator["_id"],
        name=evaluator["name"],
        judge_prompt_template=evaluator["judge_prompt_template"],
        score_scale=evaluator["score_scale"],
        active=evaluator["active"],
        created_at=evaluator["created_at"],
    )


@router.post("", response_model=EvaluatorOut)
async def create_evaluator(
    project_id: str,
    payload: EvaluatorCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> EvaluatorOut:
    await _get_owned_project(project_id, user, db)
    evaluator = {
        "_id": new_id(),
        "project_id": project_id,
        "name": payload.name,
        "judge_prompt_template": payload.judge_prompt_template,
        "score_scale": payload.score_scale,
        "active": True,
        "created_at": utcnow(),
    }
    await db.evaluators.insert_one(evaluator)
    return _to_evaluator_out(evaluator)


@router.get("", response_model=list[EvaluatorOut])
async def list_evaluators(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[EvaluatorOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.evaluators.find({"project_id": project_id}).sort("created_at", -1)
    return [_to_evaluator_out(e) async for e in cursor]


@router.patch("/{evaluator_id}", response_model=EvaluatorOut)
async def update_evaluator(
    project_id: str,
    evaluator_id: str,
    active: bool | None = Body(default=None, embed=True),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> EvaluatorOut:
    await _get_owned_project(project_id, user, db)
    if active is not None:
        await db.evaluators.update_one(
            {"_id": evaluator_id, "project_id": project_id}, {"$set": {"active": active}}
        )
    evaluator = await db.evaluators.find_one({"_id": evaluator_id, "project_id": project_id})
    if evaluator is None:
        raise HTTPException(status_code=404, detail="Evaluator not found")
    return _to_evaluator_out(evaluator)
