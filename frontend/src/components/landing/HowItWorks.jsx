const STEPS = [
  {
    label: "TRACE",
    title: "Attach the SDK",
    body: "One callback handler, attached to any chain or graph. Every step — LLM call, tool call, retrieval, chain — gets recorded with what went in, what came out, and how long it took.",
  },
  {
    label: "VIEW",
    title: "Watch it land",
    body: "Traces stream into the dashboard within seconds, rendered as a proportional waterfall — timeline bars sized by actual duration, nested by parent step.",
  },
  {
    label: "EVALUATE",
    title: "Score it automatically",
    body: "Define a judge prompt once per project. A background worker scores every completed trace against it and records the reasoning, not just a number.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto w-full max-w-5xl px-6 py-20 sm:px-10">
      <div className="mb-12 max-w-2xl border-b border-border pb-6">
        <p className="font-display text-[11px] font-medium tracking-[0.18em] text-signal uppercase">
          How it works
        </p>
        <h2 className="mt-2 font-display text-2xl font-bold text-text sm:text-3xl">
          Three steps, no dashboard tab left open all day
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
        {STEPS.map((step) => (
          <div key={step.label} className="relative pl-6">
            <span className="absolute top-1 left-0 h-3 w-3 rounded-full border-2 border-signal bg-surface" />
            <p className="font-mono text-[11px] font-semibold tracking-[0.14em] text-signal">
              {step.label}
            </p>
            <h3 className="mt-2 font-display text-lg font-semibold text-text">{step.title}</h3>
            <p className="mt-2 font-body text-sm leading-relaxed text-text-dim">{step.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
