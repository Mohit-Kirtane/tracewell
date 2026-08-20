import pytest

from app.scoring.judge import parse_score_response, render_transcript


def test_render_transcript_includes_span_name_and_output():
    spans = [
        {"name": "gemini-call", "type": "llm", "input": "How many days off?", "output": "18 days."}
    ]
    transcript = render_transcript(spans)
    assert "gemini-call" in transcript
    assert "How many days off?" in transcript
    assert "18 days." in transcript


def test_render_transcript_handles_multiple_spans_in_order():
    spans = [
        {"name": "retrieve", "type": "retriever", "input": "q", "output": "docs"},
        {"name": "generate", "type": "llm", "input": "q + docs", "output": "answer"},
    ]
    transcript = render_transcript(spans)
    assert transcript.index("retrieve") < transcript.index("generate")


def test_parse_score_response_extracts_score_and_reasoning():
    text = "SCORE: 4\nREASONING: The answer is mostly grounded in the retrieved context."
    score, reasoning = parse_score_response(text)
    assert score == "4"
    assert reasoning == "The answer is mostly grounded in the retrieved context."


def test_parse_score_response_rejects_malformed_output():
    with pytest.raises(ValueError):
        parse_score_response("I think it's pretty good, 4/5 maybe?")
