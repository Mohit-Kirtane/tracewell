import re

from app.core.llm import get_llm

_SCORE_RE = re.compile(r"SCORE:\s*(.+?)\s*\n\s*REASONING:\s*(.+)", re.DOTALL)

_JUDGE_SYSTEM_PROMPT = (
    "You are an evaluator scoring an AI agent's run against a rubric. "
    "Respond in exactly this format, with nothing else:\n"
    "SCORE: <score>\n"
    "REASONING: <one or two sentence explanation>"
)


def render_transcript(spans: list[dict]) -> str:
    lines = []
    for span in spans:
        lines.append(f"[{span['type']}] {span['name']}")
        if span.get("input"):
            lines.append(f"  input: {span['input']}")
        if span.get("output"):
            lines.append(f"  output: {span['output']}")
    return "\n".join(lines)


def parse_score_response(text: str) -> tuple[str, str]:
    match = _SCORE_RE.search(text)
    if not match:
        raise ValueError(f"Could not parse judge response: {text!r}")
    return match.group(1).strip(), match.group(2).strip()


async def score_trace(trace: dict, evaluator: dict) -> tuple[str, str]:
    transcript = render_transcript(trace["spans"])
    messages = [
        ("system", _JUDGE_SYSTEM_PROMPT),
        (
            "human",
            f"Rubric: {evaluator['judge_prompt_template']}\n"
            f"Score scale: {evaluator['score_scale']}\n\n"
            f"Agent run transcript:\n{transcript}",
        ),
    ]
    llm = get_llm()
    response = await llm.ainvoke(messages)
    return parse_score_response(response.content)
