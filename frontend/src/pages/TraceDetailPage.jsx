import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getTrace, rescoreTrace } from "../lib/api.js";
import { ScoreBadge } from "../components/ScoreBadge.jsx";
import { SpanWaterfall } from "../components/SpanWaterfall.jsx";

export default function TraceDetailPage() {
  const { traceId } = useParams();
  const [trace, setTrace] = useState(null);

  async function refresh() {
    setTrace(await getTrace(traceId));
  }

  useEffect(() => {
    refresh();
  }, [traceId]);

  if (!trace) return null;

  return (
    <div className="mx-auto mt-12 max-w-3xl p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{trace.name}</h1>
        <button
          onClick={async () => {
            await rescoreTrace(traceId);
            await refresh();
          }}
          className="rounded border px-3 py-1 text-sm"
        >
          Rescore
        </button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {trace.evaluations.map((e) => (
          <ScoreBadge key={e.evaluator_id} evaluation={e} />
        ))}
      </div>
      <div className="mt-6">
        <SpanWaterfall spans={trace.spans} />
      </div>
    </div>
  );
}
