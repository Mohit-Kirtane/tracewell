import { Logo } from "../Logo.jsx";

export function LandingFooter() {
  return (
    <footer className="mx-auto w-full max-w-5xl px-6 pb-12 sm:px-10">
      <div className="flex flex-col items-start justify-between gap-4 border-t border-border pt-6 sm:flex-row sm:items-center">
        <Logo />
        <p className="font-mono text-[11px] tracking-wide text-text-faint">
          MIT LICENSED · BUILT BY{" "}
          <a
            href="https://github.com/mohit-kirtane"
            target="_blank"
            rel="noreferrer"
            className="text-text-dim underline decoration-border underline-offset-2 transition hover:text-signal"
          >
            MOHIT KIRTANE
          </a>
        </p>
      </div>
    </footer>
  );
}
