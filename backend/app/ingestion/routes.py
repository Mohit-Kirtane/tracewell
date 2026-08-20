from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_project
from app.core.db import get_db
from app.db.ids import new_id, utcnow
from app.schemas import TraceCreate, TraceCreateOut, TraceUpdate

router = APIRouter(prefix="/v1/traces", tags=["ingestion"])


@router.post("", response_model=TraceCreateOut)
async def start_trace(
    payload: TraceCreate,
    project: dict = Depends(get_current_project),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TraceCreateOut:
    trace = {
        "_id": new_id(),
        "project_id": project["_id"],
        "name": payload.name,
        "status": "running",
        "started_at": utcnow(),
        "ended_at": None,
        "total_tokens": 0,
        "spans": [],
    }
    await db.traces.insert_one(trace)
    return TraceCreateOut(id=trace["_id"])


@router.patch("/{trace_id}")
async def update_trace(
    trace_id: str,
    payload: TraceUpdate,
    project: dict = Depends(get_current_project),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    trace = await db.traces.find_one({"_id": trace_id, "project_id": project["_id"]})
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    updates: dict = {}
    if payload.spans is not None:
        spans = [span.model_dump(mode="json") for span in payload.spans]
        updates["spans"] = spans
        updates["total_tokens"] = sum(span.get("tokens") or 0 for span in spans)
    if payload.status is not None:
        updates["status"] = payload.status
        if payload.status in ("complete", "error"):
            updates["ended_at"] = utcnow()

    if updates:
        await db.traces.update_one({"_id": trace_id}, {"$set": updates})
    return {"ok": True}
