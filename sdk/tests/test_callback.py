from unittest.mock import MagicMock
from uuid import uuid4

from tracewell_sdk.callback import TracewellCallbackHandler


def _make_handler():
    fake_client = MagicMock()
    fake_client.start_trace.return_value = "trace-abc"
    handler = TracewellCallbackHandler(client=fake_client)
    return handler, fake_client


def test_first_callback_starts_the_trace_lazily():
    handler, fake_client = _make_handler()
    fake_client.start_trace.assert_not_called()

    run_id = uuid4()
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=run_id)

    fake_client.start_trace.assert_called_once()
    assert handler.trace_id == "trace-abc"


def test_llm_start_and_end_records_one_span_with_output():
    handler, fake_client = _make_handler()
    run_id = uuid4()

    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=run_id)

    response = MagicMock()
    response.generations = [[MagicMock(text="hi there")]]
    response.llm_output = {"token_usage": {"total_tokens": 12}}
    handler.on_llm_end(response, run_id=run_id)

    assert len(handler.spans) == 1
    span = handler.spans[0]
    assert span["type"] == "llm"
    assert span["output"] == "hi there"
    assert span["tokens"] == 12
    fake_client.update_trace.assert_called_with("trace-abc", spans=handler.spans)


def test_tool_start_and_end_records_a_tool_span():
    handler, _fake_client = _make_handler()
    run_id = uuid4()

    handler.on_tool_start({"name": "search"}, "query text", run_id=run_id)
    handler.on_tool_end("search results", run_id=run_id)

    assert handler.spans[0]["type"] == "tool"
    assert handler.spans[0]["output"] == "search results"


def test_nested_span_records_parent_run_id():
    handler, _fake_client = _make_handler()
    parent_id = uuid4()
    child_id = uuid4()

    handler.on_chain_start({"name": "agent"}, {"input": "q"}, run_id=parent_id)
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=child_id, parent_run_id=parent_id)

    child_span = next(s for s in handler.spans if s["id"] == str(child_id))
    assert child_span["parent_id"] == str(parent_id)


def test_finish_marks_the_trace_complete():
    handler, fake_client = _make_handler()
    handler.on_llm_start({"name": "gemini"}, ["hello"], run_id=uuid4())

    handler.finish()

    fake_client.update_trace.assert_called_with("trace-abc", status="complete")


def test_chain_start_tolerates_serialized_being_none():
    # LangGraph fires on_chain_start with serialized=None for some of its
    # own internal orchestration steps, not just real Chains/Runnables.
    handler, fake_client = _make_handler()
    run_id = uuid4()

    handler.on_chain_start(None, {"input": "q"}, run_id=run_id)

    assert handler.trace_id == "trace-abc"
    assert handler.spans[0]["name"] == "chain"


def test_llm_start_tolerates_serialized_being_none():
    handler, _fake_client = _make_handler()
    run_id = uuid4()

    handler.on_llm_start(None, ["hello"], run_id=run_id)

    assert handler.spans[0]["name"] == "llm"


def test_record_end_is_a_noop_if_no_trace_was_ever_started():
    # If every *_start callback for this run failed before _ensure_trace()
    # ran, trace_id stays None - _record_end must not call the client with
    # a None trace id.
    handler, fake_client = _make_handler()

    handler.on_llm_end(MagicMock(generations=[], llm_output=None), run_id=uuid4())

    fake_client.update_trace.assert_not_called()
