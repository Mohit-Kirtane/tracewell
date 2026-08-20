import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { listProjects } from "../lib/api.js";
import { Logo } from "./Logo.jsx";

const TAB_CLASS = ({ isActive }) =>
  `border-b-2 px-1 pb-3 pt-3 font-body text-sm font-medium transition ${
    isActive ? "border-signal text-text" : "border-transparent text-text-dim hover:text-text"
  }`;

export function DashboardLayout() {
  const { projectId } = useParams();
  const { user, logout } = useAuth();
  const [projectName, setProjectName] = useState(null);

  useEffect(() => {
    if (!projectId) {
      setProjectName(null);
      return;
    }
    listProjects().then((projects) => {
      setProjectName(projects.find((p) => p.id === projectId)?.name ?? null);
    });
  }, [projectId]);

  return (
    <div className="min-h-screen bg-bg">
      <header className="relative border-b border-border bg-surface">
        <div className="absolute top-0 left-0 h-[2px] w-full overflow-hidden bg-border">
          <div className="scan-line h-full w-1/4 bg-gradient-to-r from-transparent via-signal to-transparent" />
        </div>
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/projects">
            <Logo />
          </Link>
          <div className="flex items-center gap-4">
            <span className="font-mono text-xs text-text-dim">{user?.email}</span>
            <button
              onClick={logout}
              className="font-body text-sm text-text-dim transition hover:text-text"
            >
              Sign out
            </button>
          </div>
        </div>
        {projectId && (
          <div className="mx-auto max-w-5xl px-6">
            <div className="flex items-center gap-6">
              <Link
                to="/projects"
                className="font-body text-sm text-text-dim transition hover:text-text"
              >
                ← Projects
              </Link>
              <span className="font-display text-sm font-semibold text-text">
                {projectName ?? "…"}
              </span>
              <nav className="ml-4 flex items-center gap-5">
                <NavLink to={`/projects/${projectId}/traces`} className={TAB_CLASS}>
                  Traces
                </NavLink>
                <NavLink to={`/projects/${projectId}/evaluators`} className={TAB_CLASS}>
                  Evaluators
                </NavLink>
                <NavLink to={`/projects/${projectId}/api-keys`} className={TAB_CLASS}>
                  API keys
                </NavLink>
              </nav>
            </div>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
