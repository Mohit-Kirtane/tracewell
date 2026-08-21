import { Link } from "react-router-dom";
import { Logo } from "../Logo.jsx";

export function LandingHeader() {
  return (
    <header className="relative border-b border-border bg-surface">
      <div className="absolute top-0 left-0 h-[2px] w-full overflow-hidden bg-border">
        <div className="scan-line h-full w-1/4 bg-gradient-to-r from-transparent via-signal to-transparent" />
      </div>
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4 sm:px-10">
        <Link to="/">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-7 font-body text-sm font-medium text-text-dim md:flex">
          <a href="#how-it-works" className="transition hover:text-text">
            How it works
          </a>
          <a href="#features" className="transition hover:text-text">
            Features
          </a>
          <a
            href="https://github.com/Mohit-Kirtane/tracewell"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-text"
          >
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="hidden font-body text-sm font-medium text-text-dim transition hover:text-text sm:inline"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="rounded-md bg-signal px-4 py-2 font-display text-[13px] font-medium tracking-wide text-white transition hover:bg-signal-deep"
          >
            GET STARTED
          </Link>
        </div>
      </div>
    </header>
  );
}
