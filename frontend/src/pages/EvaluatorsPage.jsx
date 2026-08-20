import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { createEvaluator, listEvaluators, updateEvaluator } from "../lib/api.js";

export default function EvaluatorsPage() {
  const { projectId } = useParams();
  const [evaluators, setEvaluators] = useState(null);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setEvaluators(await listEvaluators(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim() || !prompt.trim()) return;
    setCreating(true);
    try {
      await createEvaluator(projectId, name.trim(), prompt.trim());
      setName("");
      setPrompt("");
      await refresh();
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(evaluatorId, active) {
    await updateEvaluator(projectId, evaluatorId, !active);
    await refresh();
  }

  return (
    <div>
      <h1 className="border-b border-border pb-5 font-display text-xl font-semibold text-text">
        Evaluators
      </h1>

      <form
        onSubmit={handleCreate}
        className="mt-5 flex flex-col gap-3 rounded-lg border border-border bg-surface p-4"
      >
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Evaluator name (e.g. Groundedness)"
          className="rounded-md border border-border bg-bg px-3.5 py-2.5 font-body text-sm text-text outline-none placeholder:text-text-faint focus:border-signal"
        />
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Judge prompt / rubric — e.g. &quot;Is the answer grounded in the retrieved context?&quot;"
          className="rounded-md border border-border bg-bg px-3.5 py-2.5 font-body text-sm text-text outline-none placeholder:text-text-faint focus:border-signal"
          rows={3}
        />
        <button
          type="submit"
          disabled={creating || !name.trim() || !prompt.trim()}
          className="flex items-center gap-1.5 self-start rounded-md bg-signal px-4 py-2 font-body text-sm font-medium text-white transition hover:bg-signal-deep disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus className="h-3.5 w-3.5" />
          Add evaluator
        </button>
      </form>

      {evaluators === null ? null : evaluators.length === 0 ? (
        <div className="mt-6 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center">
          <p className="font-body text-sm text-text-dim">
            No evaluators yet. Add one and every completed trace gets scored against it.
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-2">
          {evaluators.map((e) => (
            <li key={e.id} className="rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="font-body text-sm font-semibold text-text">{e.name}</span>
                <button
                  onClick={() => toggleActive(e.id, e.active)}
                  className={`rounded-full px-2.5 py-1 font-body text-xs font-medium transition ${
                    e.active ? "bg-ok-tint text-ok" : "bg-surface-sunken text-text-dim"
                  }`}
                >
                  {e.active ? "Active" : "Inactive"}
                </button>
              </div>
              <p className="mt-2 font-body text-sm text-text-dim">{e.judge_prompt_template}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
