import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.db import get_database
from app.db.ids import new_id, utcnow
from app.scoring.judge import score_trace


async def _find_unscored_pair(db: AsyncIOMotorDatabase) -> tuple[dict, dict] | None:
    async for trace in db.traces.find({"status": "complete"}):
        async for evaluator in db.evaluators.find(
            {"project_id": trace["project_id"], "active": True}
        ):
            existing = await db.evaluations.find_one(
                {"trace_id": trace["_id"], "evaluator_id": evaluator["_id"]}
            )
            if existing is None:
                return trace, evaluator
    return None


async def poll_once(db: AsyncIOMotorDatabase) -> int:
    pair = await _find_unscored_pair(db)
    if pair is None:
        return 0
    trace, evaluator = pair

    try:
        score, reasoning = await score_trace(trace, evaluator)
        status = "done"
    except Exception as exc:  # noqa: BLE001 - any judge failure is recorded, not raised
        score, reasoning, status = None, str(exc), "failed"

    await db.evaluations.insert_one(
        {
            "_id": new_id(),
            "trace_id": trace["_id"],
            "evaluator_id": evaluator["_id"],
            "score": score,
            "reasoning": reasoning,
            "status": status,
            "created_at": utcnow(),
        }
    )
    return 1


async def run_forever() -> None:
    settings = get_settings()
    db = get_database()
    while True:
        await poll_once(db)
        await asyncio.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_forever())
