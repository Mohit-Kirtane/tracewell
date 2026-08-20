import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { createEvaluator, listEvaluators, updateEvaluator } from "../lib/api.js";

export default function EvaluatorsPage() {
  const { projectId } = useParams();
  const [evaluators, setEvaluators] = useState([]);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");

  async function refresh() {
    setEvaluators(await listEvaluators(projectId));
  }

  useEffect(() => {
    refresh();
  }, [projectId]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim() || !prompt.trim()) return;
    await createEvaluator(projectId, name.trim(), prompt.trim());
    setName("");
    setPrompt("");
    await refresh();
  }

  async function toggleActive(evaluatorId, active) {
    await updateEvaluator(projectId, evaluatorId, !active);
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">Evaluators</h1>
      <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Evaluator name (e.g. Groundedness)"
          className="rounded border px-3 py-2"
        />
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Judge prompt / rubric"
          className="rounded border px-3 py-2"
          rows={3}
        />
        <button type="submit" className="self-start rounded bg-black px-4 py-2 text-white">
          Add evaluator
        </button>
      </form>
      <ul className="mt-6 flex flex-col gap-2">
        {evaluators.map((e) => (
          <li key={e.id} className="rounded border p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium">{e.name}</span>
              <button onClick={() => toggleActive(e.id, e.active)} className="text-sm underline">
                {e.active ? "Deactivate" : "Activate"}
              </button>
            </div>
            <p className="mt-1 text-sm text-gray-600">{e.judge_prompt_template}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
