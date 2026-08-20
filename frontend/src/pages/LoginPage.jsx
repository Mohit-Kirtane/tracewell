import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { login } from "../lib/api.js";
import { Logo } from "../components/Logo.jsx";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      await refresh();
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="rounded-lg border border-border bg-surface p-7 shadow-sm">
          <h1 className="font-display text-lg font-semibold text-text">Sign in</h1>
          <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-3">
            <input
              type="email"
              required
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-border bg-bg px-3.5 py-2.5 font-body text-sm text-text outline-none placeholder:text-text-faint focus:border-signal"
            />
            <input
              type="password"
              required
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border border-border bg-bg px-3.5 py-2.5 font-body text-sm text-text outline-none placeholder:text-text-faint focus:border-signal"
            />
            {error && <p className="font-body text-sm text-danger">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="mt-1 rounded-md bg-signal px-4 py-2.5 font-body text-sm font-medium text-white transition hover:bg-signal-deep disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
        <p className="mt-5 text-center font-body text-sm text-text-dim">
          No account?{" "}
          <Link to="/register" className="font-medium text-signal hover:text-signal-deep">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
