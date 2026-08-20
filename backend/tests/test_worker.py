from unittest.mock import AsyncMock, patch

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.worker import poll_once

pytestmark = pytest.mark.asyncio


async def _seed_complete_trace_with_active_evaluator(db):
    await db.projects.insert_one({"_id": "proj-1", "user_id": "user-1", "name": "P"})
    await db.evaluators.insert_one(
        {
            "_id": "eval-1",
            "project_id": "proj-1",
            "name": "Groundedness",
            "judge_prompt_template": "Is it grounded?",
            "score_scale": "1-5",
            "active": True,
        }
    )
    await db.traces.insert_one(
        {
            "_id": "trace-1",
            "project_id": "proj-1",
            "name": "run",
            "status": "complete",
            "spans": [{"type": "llm", "name": "call", "input": "q", "output": "a"}],
        }
    )


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_scores_a_pending_trace(mock_score_trace):
    mock_score_trace.return_value = ("4", "Mostly grounded.")
    db = AsyncMongoMockClient()["worker_test"]
    await _seed_complete_trace_with_active_evaluator(db)

    scored_count = await poll_once(db)

    assert scored_count == 1
    evaluation = await db.evaluations.find_one({"trace_id": "trace-1", "evaluator_id": "eval-1"})
    assert evaluation["status"] == "done"
    assert evaluation["score"] == "4"


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_does_nothing_when_no_traces_are_pending(mock_score_trace):
    db = AsyncMongoMockClient()["worker_test_empty"]
    scored_count = await poll_once(db)
    assert scored_count == 0
    mock_score_trace.assert_not_called()


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_skips_traces_already_evaluated(mock_score_trace):
    db = AsyncMongoMockClient()["worker_test_skip"]
    await _seed_complete_trace_with_active_evaluator(db)
    await db.evaluations.insert_one(
        {
            "_id": "existing-eval",
            "trace_id": "trace-1",
            "evaluator_id": "eval-1",
            "score": "5",
            "reasoning": "already scored",
            "status": "done",
        }
    )

    scored_count = await poll_once(db)

    assert scored_count == 0
    mock_score_trace.assert_not_called()


@patch("app.worker.score_trace", new_callable=AsyncMock)
async def test_poll_once_marks_evaluation_failed_when_judge_errors(mock_score_trace):
    mock_score_trace.side_effect = ValueError("judge output unparseable")
    db = AsyncMongoMockClient()["worker_test_fail"]
    await _seed_complete_trace_with_active_evaluator(db)

    scored_count = await poll_once(db)

    assert scored_count == 1
    evaluation = await db.evaluations.find_one({"trace_id": "trace-1", "evaluator_id": "eval-1"})
    assert evaluation["status"] == "failed"
    assert "judge output unparseable" in evaluation["reasoning"]
