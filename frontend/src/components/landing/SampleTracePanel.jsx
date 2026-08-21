import { ScoreBadge } from "../ScoreBadge.jsx";
import { SpanWaterfall } from "../SpanWaterfall.jsx";

const SAMPLE_SPANS = [
  {
    id: "s1",
    parent_id: null,
    type: "chain",
    name: "policy_retrieval",
    input: "Can the employee role see the compensation policy?",
    output: null,
    started_at: "2026-08-21T09:00:00.000Z",
    ended_at: "2026-08-21T09:00:01.850Z",
    tokens: null,
    error: null,
  },
  {
    id: "s2",
    parent_id: "s1",
    type: "retriever",
    name: "policy_search",
    input: "compensation policy access",
    output: "3 chunks retrieved, role-filtered",
    started_at: "2026-08-21T09:00:00.050Z",
    ended_at: "2026-08-21T09:00:00.210Z",
    tokens: null,
    error: null,
  },
  {
    id: "s3",
    parent_id: "s1",
    type: "llm",
    name: "gemini-3.6-flash",
    input: "Answer using only the retrieved excerpts…",
    output: "That's outside what the employee role can access.",
    started_at: "2026-08-21T09:00:00.230Z",
    ended_at: "2026-08-21T09:00:01.820Z",
    tokens: 214,
    error: null,
  },
];

const SAMPLE_EVALUATIONS = [
  { evaluator_id: "e1", evaluator_name: "Groundedness", score: "5", status: "done" },
  { evaluator_id: "e2", evaluator_name: "Access correctness", score: "5", status: "done" },
];

export function SampleTracePanel() {
  return (
    <div className="w-full max-w-md rounded-xl border border-border bg-surface shadow-[0_30px_60px_-30px_rgba(15,23,42,0.25)]">
      <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
        <div>
          <p className="font-display text-sm font-semibold text-text">policy_retrieval</p>
          <p className="font-mono text-[11px] text-text-faint">214 tokens · 3 spans</p>
        </div>
        <span className="rounded-full bg-ok-tint px-2 py-0.5 font-mono text-[10px] font-medium text-ok uppercase">
          complete
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 border-b border-border px-5 py-3">
        {SAMPLE_EVALUATIONS.map((e) => (
          <ScoreBadge key={e.evaluator_id} evaluation={e} />
        ))}
      </div>

      <div className="p-2">
        <SpanWaterfall spans={SAMPLE_SPANS} />
      </div>
    </div>
  );
}
