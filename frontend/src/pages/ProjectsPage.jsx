import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Plus } from "lucide-react";
import { createProject, listProjects } from "../lib/api.js";

export default function ProjectsPage() {
  const [projects, setProjects] = useState(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setProjects(await listProjects());
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createProject(name.trim());
      setName("");
      await refresh();
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between border-b border-border pb-5">
        <h1 className="font-display text-xl font-semibold text-text">Projects</h1>
      </div>

      <form onSubmit={handleCreate} className="mt-5 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          className="flex-1 rounded-md border border-border bg-surface px-3.5 py-2.5 font-body text-sm text-text outline-none placeholder:text-text-faint focus:border-signal"
        />
        <button
          type="submit"
          disabled={creating || !name.trim()}
          className="flex items-center gap-1.5 rounded-md bg-signal px-4 py-2.5 font-body text-sm font-medium text-white transition hover:bg-signal-deep disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
          Create
        </button>
      </form>

      {projects === null ? null : projects.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-border-strong px-6 py-10 text-center">
          <p className="font-body text-sm text-text-dim">
            No projects yet. Create one to get an API key and start sending traces.
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-2">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}/traces`}
                className="group flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3.5 transition hover:border-signal"
              >
                <span className="font-body text-sm font-medium text-text">{p.name}</span>
                <ArrowRight className="h-4 w-4 text-text-faint transition group-hover:text-signal" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
