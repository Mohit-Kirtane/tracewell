import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { login } from "../lib/api.js";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      await refresh();
      navigate("/projects", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="mx-auto mt-24 max-w-sm p-6">
      <h1 className="text-xl font-semibold">Sign in</h1>
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" className="rounded bg-black px-4 py-2 text-white">
          Sign in
        </button>
      </form>
      <p className="mt-3 text-sm">
        No account? <Link to="/register" className="underline">Register</Link>
      </p>
    </div>
  );
}
