import { useState } from "react";

const TYPE_COLOR = {
  chain: "bg-zinc-400",
  llm: "bg-signal",
  tool: "bg-violet-500",
  retriever: "bg-warn",
};

function depthOf(span, byId, cache = new Map()) {
  if (cache.has(span.id)) return cache.get(span.id);
  if (!span.parent_id || !byId.has(span.parent_id)) {
    cache.set(span.id, 0);
    return 0;
  }
  const depth = 1 + depthOf(byId.get(span.parent_id), byId, cache);
  cache.set(span.id, depth);
  return depth;
}

export function SpanWaterfall({ spans }) {
  const [expandedId, setExpandedId] = useState(null);

  if (spans.length === 0) {
    return <p className="font-body text-sm text-text-dim">No spans recorded for this trace.</p>;
  }

  const byId = new Map(spans.map((s) => [s.id, s]));
  const starts = spans.map((s) => new Date(s.started_at).getTime());
  const ends = spans.map((s) => new Date(s.ended_at ?? s.started_at).getTime());
  const timelineStart = Math.min(...starts);
  const timelineEnd = Math.max(...ends);
  const totalMs = Math.max(timelineEnd - timelineStart, 1);

  const sorted = [...spans].sort((a, b) => new Date(a.started_at) - new Date(b.started_at));

  return (
    <div className="rounded-lg border border-border bg-surface">
      {sorted.map((span, i) => {
        const depth = depthOf(span, byId);
        const startMs = new Date(span.started_at).getTime();
        const endMs = new Date(span.ended_at ?? span.started_at).getTime();
        const durationMs = Math.max(endMs - startMs, 0);
        const leftPct = ((startMs - timelineStart) / totalMs) * 100;
        const widthPct = Math.max((durationMs / totalMs) * 100, 0.6);
        const expanded = expandedId === span.id;

        return (
          <div key={span.id} className={i > 0 ? "border-t border-border" : ""}>
            <button
              onClick={() => setExpandedId(expanded ? null : span.id)}
              className="flex w-full items-center gap-4 px-4 py-2.5 text-left transition hover:bg-surface-sunken"
            >
              <div className="w-56 shrink-0 truncate" style={{ paddingLeft: `${depth * 14}px` }}>
                <span className="font-body text-sm font-medium text-text">{span.name}</span>
                <span className="ml-1.5 font-mono text-xs text-text-faint">{span.type}</span>
              </div>
              <div className="relative h-5 flex-1">
                <div
                  className={`absolute top-1/2 h-2 -translate-y-1/2 rounded-full ${TYPE_COLOR[span.type] ?? "bg-zinc-400"} ${span.error ? "ring-2 ring-danger" : ""}`}
                  style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                />
              </div>
              <span className="w-16 shrink-0 text-right font-mono text-xs text-text-dim">
                {durationMs}ms
              </span>
            </button>
            {expanded && (
              <div className="border-t border-border bg-surface-sunken px-4 py-3">
                {span.error && (
                  <p className="mb-2 font-mono text-xs text-danger">error: {span.error}</p>
                )}
                {span.input && (
                  <div className="mb-2">
                    <p className="font-body text-xs font-medium text-text-dim">Input</p>
                    <p className="mt-0.5 whitespace-pre-wrap font-mono text-xs text-text">
                      {span.input}
                    </p>
                  </div>
                )}
                {span.output && (
                  <div>
                    <p className="font-body text-xs font-medium text-text-dim">Output</p>
                    <p className="mt-0.5 whitespace-pre-wrap font-mono text-xs text-text">
                      {span.output}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
