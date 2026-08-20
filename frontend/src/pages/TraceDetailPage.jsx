import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RotateCcw } from "lucide-react";
import { getTrace, rescoreTrace } from "../lib/api.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";
import { SpanWaterfall } from "../components/SpanWaterfall.jsx";

export default function TraceDetailPage() {
  const { projectId, traceId } = useParams();
  const [trace, setTrace] = useState(null);
  const [rescoring, setRescoring] = useState(false);
  const [justLandedIds, setJustLandedIds] = useState(new Set());
  const prevStatuses = useRef(new Map());

  async function refresh() {
    const data = await getTrace(traceId);
    const landed = new Set();
    for (const evaluation of data.evaluations) {
      const prev = prevStatuses.current.get(evaluation.evaluator_id);
      if (prev && prev !== "done" && evaluation.status === "done") {
        landed.add(evaluation.evaluator_id);
      }
      prevStatuses.current.set(evaluation.evaluator_id, evaluation.status);
    }
    setJustLandedIds(landed);
    setTrace(data);
  }

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      if (cancelled) return;
      await refresh();
    }
    tick();
    const interval = setInterval(tick, 4000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [traceId]);

  if (!trace) return null;

  async function handleRescore() {
    setRescoring(true);
    prevStatuses.current.clear();
    try {
      await rescoreTrace(traceId);
      await refresh();
    } finally {
      setRescoring(false);
    }
  }

  return (
    <div>
      <Link
        to={`/projects/${projectId}/traces`}
        className="font-body text-sm text-text-dim hover:text-text"
      >
        ← Traces
      </Link>

      <div className="mt-3 flex items-center justify-between border-b border-border pb-5">
        <div>
          <h1 className="font-display text-xl font-semibold text-text">{trace.name}</h1>
          <p className="mt-1 font-mono text-xs text-text-faint">
            {trace.total_tokens} tokens · {trace.spans.length} spans
          </p>
        </div>
        <button
          onClick={handleRescore}
          disabled={rescoring}
          className="flex items-center gap-1.5 rounded-md border border-border px-3.5 py-2 font-body text-sm font-medium text-text transition hover:border-signal disabled:opacity-50"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Rescore
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {trace.evaluations.length === 0 ? (
          <p className="flex items-center gap-1.5 font-body text-sm text-text-faint">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-text-faint" />
            waiting on evaluators…
          </p>
        ) : (
          trace.evaluations.map((e) => (
            <ScoreBadge
              key={e.evaluator_id}
              evaluation={e}
              justLanded={justLandedIds.has(e.evaluator_id)}
            />
          ))
        )}
      </div>

      <div className="mt-6">
        <SpanWaterfall spans={trace.spans} />
      </div>
    </div>
  );
}
