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

function durationMs(span) {
  if (!span.ended_at) return null;
  return new Date(span.ended_at) - new Date(span.started_at);
}

export function SpanWaterfall({ spans }) {
  const byId = new Map(spans.map((s) => [s.id, s]));
  const sorted = [...spans].sort((a, b) => new Date(a.started_at) - new Date(b.started_at));

  return (
    <ol className="flex flex-col gap-1">
      {sorted.map((span) => {
        const depth = depthOf(span, byId);
        const ms = durationMs(span);
        return (
          <li key={span.id} style={{ marginLeft: `${depth * 20}px` }} className="rounded border p-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                [{span.type}] {span.name}
              </span>
              {ms !== null && <span className="text-gray-500">{ms}ms</span>}
            </div>
            {span.input && <p className="mt-1 truncate text-xs text-gray-600">in: {span.input}</p>}
            {span.output && <p className="truncate text-xs text-gray-600">out: {span.output}</p>}
            {span.error && <p className="text-xs text-red-600">error: {span.error}</p>}
          </li>
        );
      })}
    </ol>
  );
}
