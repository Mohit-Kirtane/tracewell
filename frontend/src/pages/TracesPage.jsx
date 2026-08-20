import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listTraces } from "../lib/api.js";

const STATUS_STYLE = {
  complete: "bg-ok-tint text-ok",
  running: "bg-warn-tint text-warn",
  error: "bg-danger-tint text-danger",
};

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-mono text-xs font-medium ${STATUS_STYLE[status] ?? "bg-surface-sunken text-text-dim"}`}
    >
      {status === "running" && <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-warn" />}
      {status}
    </span>
  );
}

export default function TracesPage() {
  const { projectId } = useParams();
  const [traces, setTraces] = useState(null);

  useEffect(() => {
    let cancelled = false;
    function refresh() {
      listTraces(projectId).then((data) => {
        if (!cancelled) setTraces(data);
      });
    }
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [projectId]);

  return (
    <div>
      <div className="flex items-center justify-between border-b border-border pb-5">
        <h1 className="font-display text-xl font-semibold text-text">Traces</h1>
        <span className="flex items-center gap-1.5 font-mono text-xs text-text-faint">
          <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-signal" />
          watching for new traces
        </span>
      </div>

      {traces === null ? null : traces.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center">
          <p className="font-body text-sm text-text-dim">
            Nothing traced yet — send a run from an agent using tracewell-sdk and it'll appear
            here the moment it lands.
          </p>
        </div>
      ) : (
        <div className="mt-5 overflow-hidden rounded-lg border border-border">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border bg-surface-sunken">
                <th className="px-4 py-2.5 font-body text-xs font-medium text-text-dim">Name</th>
                <th className="px-4 py-2.5 font-body text-xs font-medium text-text-dim">Status</th>
                <th className="px-4 py-2.5 font-body text-xs font-medium text-text-dim">Spans</th>
                <th className="px-4 py-2.5 font-body text-xs font-medium text-text-dim">Tokens</th>
                <th className="px-4 py-2.5 font-body text-xs font-medium text-text-dim">Started</th>
              </tr>
            </thead>
            <tbody className="bg-surface">
              {traces.map((t) => (
                <tr key={t.id} className="border-b border-border last:border-0 hover:bg-surface-sunken">
                  <td className="px-4 py-3">
                    <Link to={`/projects/${projectId}/traces/${t.id}`} className="font-body text-sm font-medium text-signal hover:underline">
                      {t.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="px-4 py-3 font-mono text-sm text-text-dim">{t.span_count}</td>
                  <td className="px-4 py-3 font-mono text-sm text-text-dim">{t.total_tokens}</td>
                  <td className="px-4 py-3 font-mono text-xs text-text-faint">
                    {new Date(t.started_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
