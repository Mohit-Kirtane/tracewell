const STACK = ["PYTHON", "FASTAPI", "MONGODB", "LANGCHAIN", "REACT", "GEMINI"];

export function TechStack() {
  return (
    <section className="mx-auto w-full max-w-5xl px-6 py-14 sm:px-10">
      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-10">
        <span className="mr-2 font-mono text-[11px] tracking-[0.18em] text-text-faint">
          BUILT WITH
        </span>
        {STACK.map((name) => (
          <span
            key={name}
            className="rounded border border-border px-2.5 py-1 font-mono text-[11px] tracking-wide text-text-dim"
          >
            {name}
          </span>
        ))}
      </div>
    </section>
  );
}
