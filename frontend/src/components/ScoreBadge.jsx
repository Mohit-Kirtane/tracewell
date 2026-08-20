export function ScoreBadge({ evaluation }) {
  const color =
    evaluation.status === "done"
      ? "bg-green-100 text-green-800"
      : evaluation.status === "failed"
        ? "bg-red-100 text-red-800"
        : "bg-gray-100 text-gray-600";

  return (
    <span className={`rounded px-2 py-0.5 text-xs ${color}`}>
      {evaluation.evaluator_name}: {evaluation.status === "done" ? evaluation.score : evaluation.status}
    </span>
  );
}
