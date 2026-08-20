const STATUS_STYLE = {
  done: "bg-ok-tint text-ok",
  failed: "bg-danger-tint text-danger",
  pending: "bg-warn-tint text-warn",
};

export function ScoreBadge({ evaluation, justLanded }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-body text-xs font-medium ${
        STATUS_STYLE[evaluation.status] ?? "bg-surface-sunken text-text-dim"
      } ${justLanded ? "score-land" : ""}`}
    >
      {evaluation.status === "pending" && (
        <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-warn" />
      )}
      {evaluation.evaluator_name}
      {evaluation.status === "done" && <span className="font-mono">{evaluation.score}</span>}
      {evaluation.status !== "done" && <span>· {evaluation.status}</span>}
    </span>
  );
}
