from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from tracewell_sdk.client import TracewellClient


class TracewellCallbackHandler(BaseCallbackHandler):
    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.tracewell.dev",
        client: TracewellClient | None = None,
    ) -> None:
        self.client = client or TracewellClient(api_key=api_key, base_url=base_url)
        self.trace_id: str | None = None
        self.spans: list[dict[str, Any]] = []

    def _ensure_trace(self) -> None:
        if self.trace_id is None:
            self.trace_id = self.client.start_trace(name="agent-run")

    def _record_start(
        self, run_id: UUID, parent_run_id: UUID | None, span_type: str, name: str, input_text: str
    ) -> None:
        self._ensure_trace()
        self.spans.append(
            {
                "id": str(run_id),
                "parent_id": str(parent_run_id) if parent_run_id else None,
                "type": span_type,
                "name": name,
                "input": input_text,
                "output": None,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": None,
                "tokens": None,
                "error": None,
            }
        )

    def _record_end(self, run_id: UUID, output_text: str, tokens: int | None = None) -> None:
        if self.trace_id is None:
            # No span was ever successfully started for this trace (e.g. the
            # matching *_start callback failed) - nothing to update.
            return
        for span in self.spans:
            if span["id"] == str(run_id):
                span["output"] = output_text
                span["ended_at"] = datetime.now(timezone.utc).isoformat()
                span["tokens"] = tokens
                break
        self.client.update_trace(self.trace_id, spans=self.spans)

    @staticmethod
    def _serialized_name(serialized: dict | None, default: str) -> str:
        # LangGraph fires callbacks with serialized=None for some of its
        # internal orchestration steps (not just real Chains/Runnables).
        return (serialized or {}).get("name", default)

    def on_chain_start(
        self, serialized: dict | None, inputs: dict, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: Any
    ) -> None:
        self._record_start(
            run_id, parent_run_id, "chain", self._serialized_name(serialized, "chain"), str(inputs)
        )

    def on_chain_end(self, outputs: dict, *, run_id: UUID, **kwargs: Any) -> None:
        self._record_end(run_id, str(outputs))

    def on_llm_start(
        self,
        serialized: dict | None,
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._record_start(
            run_id, parent_run_id, "llm", self._serialized_name(serialized, "llm"), "\n".join(prompts)
        )

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        text = response.generations[0][0].text if response.generations else ""
        tokens = None
        if response.llm_output and "token_usage" in response.llm_output:
            tokens = response.llm_output["token_usage"].get("total_tokens")
        self._record_end(run_id, text, tokens=tokens)

    def on_tool_start(
        self,
        serialized: dict | None,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        self._record_start(
            run_id, parent_run_id, "tool", self._serialized_name(serialized, "tool"), input_str
        )

    def on_tool_end(self, output: Any, *, run_id: UUID, **kwargs: Any) -> None:
        self._record_end(run_id, str(output))

    def finish(self, status: str = "complete") -> None:
        if self.trace_id is not None:
            self.client.update_trace(self.trace_id, status=status)
