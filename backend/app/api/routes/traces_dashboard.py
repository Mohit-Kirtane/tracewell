from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.core.db import get_db
from app.schemas import EvaluationOut, SpanIn, TraceDetailOut, TraceSummaryOut

router = APIRouter(tags=["traces-dashboard"])


async def _get_owned_project(project_id: str, user: dict, db: AsyncIOMotorDatabase) -> dict:
    project = await db.projects.find_one({"_id": project_id, "user_id": user["_id"]})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_summary_out(trace: dict) -> TraceSummaryOut:
    return TraceSummaryOut(
        id=trace["_id"],
        name=trace["name"],
        status=trace["status"],
        started_at=trace["started_at"],
        ended_at=trace["ended_at"],
        total_tokens=trace["total_tokens"],
        span_count=len(trace["spans"]),
    )


@router.get("/projects/{project_id}/traces", response_model=list[TraceSummaryOut])
async def list_traces(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[TraceSummaryOut]:
    await _get_owned_project(project_id, user, db)
    cursor = db.traces.find({"project_id": project_id}).sort("started_at", -1)
    return [_to_summary_out(t) async for t in cursor]


@router.get("/traces/{trace_id}", response_model=TraceDetailOut)
async def get_trace(
    trace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TraceDetailOut:
    trace = await db.traces.find_one({"_id": trace_id})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    await _get_owned_project(trace["project_id"], user, db)

    evaluations = []
    async for evaluation in db.evaluations.find({"trace_id": trace_id}):
        evaluator = await db.evaluators.find_one({"_id": evaluation["evaluator_id"]})
        evaluations.append(
            EvaluationOut(
                evaluator_id=evaluation["evaluator_id"],
                evaluator_name=evaluator["name"] if evaluator else "(deleted evaluator)",
                score=evaluation.get("score"),
                reasoning=evaluation.get("reasoning"),
                status=evaluation["status"],
            )
        )

    return TraceDetailOut(
        id=trace["_id"],
        project_id=trace["project_id"],
        name=trace["name"],
        status=trace["status"],
        started_at=trace["started_at"],
        ended_at=trace["ended_at"],
        total_tokens=trace["total_tokens"],
        spans=[SpanIn(**span) for span in trace["spans"]],
        evaluations=evaluations,
    )


@router.post("/traces/{trace_id}/rescore")
async def rescore_trace(
    trace_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    trace = await db.traces.find_one({"_id": trace_id})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    await _get_owned_project(trace["project_id"], user, db)

    await db.evaluations.delete_many({"trace_id": trace_id})
    return {"ok": True}
