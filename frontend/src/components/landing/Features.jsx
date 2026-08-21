import { Layers, ShieldCheck, Sparkles } from "lucide-react";

const FEATURES = [
  {
    icon: Layers,
    title: "Real waterfalls, not log dumps",
    body: "Spans render as proportional timeline bars, nested by parent step, color-coded by type. Click any span to see its full input and output.",
  },
  {
    icon: Sparkles,
    title: "Judge prompts you write",
    body: "No fixed rubric. Define exactly what \"good\" means for your agent — groundedness, tone, access correctness — and score against it automatically.",
  },
  {
    icon: ShieldCheck,
    title: "A project per team, keys per project",
    body: "Real accounts, real projects, per-project API keys shown once and hashed at rest. Tracing never touches your app's own auth.",
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto w-full max-w-5xl bg-bg-subtle px-6 py-20 sm:px-10">
      <div className="mb-12 max-w-2xl border-b border-border pb-6">
        <p className="font-display text-[11px] font-medium tracking-[0.18em] text-signal uppercase">
          Features
        </p>
        <h2 className="mt-2 font-display text-2xl font-bold text-text sm:text-3xl">
          Built for agents that actually ship
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-xl border border-border bg-surface p-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-signal/10 text-signal">
              <Icon className="h-5 w-5" />
            </span>
            <h3 className="mt-4 font-display text-base font-semibold text-text">{title}</h3>
            <p className="mt-2 font-body text-sm leading-relaxed text-text-dim">{body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
