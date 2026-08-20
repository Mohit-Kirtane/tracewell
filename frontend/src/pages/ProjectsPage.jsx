import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects } from "../lib/api.js";

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");

  async function refresh() {
    setProjects(await listProjects());
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    await createProject(name.trim());
    setName("");
    await refresh();
  }

  return (
    <div className="mx-auto mt-12 max-w-2xl p-6">
      <h1 className="text-xl font-semibold">Projects</h1>
      <form onSubmit={handleCreate} className="mt-4 flex gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          className="flex-1 rounded border px-3 py-2"
        />
        <button type="submit" className="rounded bg-black px-4 py-2 text-white">
          Create
        </button>
      </form>
      <ul className="mt-6 flex flex-col gap-2">
        {projects.map((p) => (
          <li key={p.id} className="rounded border p-3">
            <Link to={`/projects/${p.id}/traces`} className="font-medium">
              {p.name}
            </Link>
            {" · "}
            <Link to={`/projects/${p.id}/api-keys`} className="text-sm underline">
              API keys
            </Link>
            {" · "}
            <Link to={`/projects/${p.id}/evaluators`} className="text-sm underline">
              Evaluators
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
