import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { SampleTracePanel } from "./SampleTracePanel.jsx";

export function Hero() {
  return (
    <section className="mx-auto grid w-full max-w-5xl grid-cols-1 items-center gap-14 px-6 pt-16 pb-20 sm:px-10 lg:grid-cols-[1.05fr_1fr] lg:gap-12 lg:pt-24">
      <div>
        <p className="font-display text-[11px] font-medium tracking-[0.18em] text-signal uppercase">
          Observability for LangChain &amp; LangGraph agents
        </p>
        <h1 className="mt-5 font-display text-[2.5rem] leading-[1.08] font-bold text-text sm:text-[3.1rem]">
          See what your agent
          <br />
          actually did.
        </h1>
        <p className="mt-6 max-w-lg font-body text-lg leading-relaxed text-text-dim">
          Drop a callback handler into your agent and every LLM call, tool call, and
          retrieval step shows up as a trace — a real waterfall, not a wall of logs.
          Define a judge prompt once, and every run gets scored automatically.
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link
            to="/register"
            className="group flex items-center gap-2 rounded-md bg-signal px-5 py-3 font-display text-[13px] font-medium tracking-wide text-white transition hover:bg-signal-deep"
          >
            GET STARTED FREE
            <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
          </Link>
          <a
            href="https://github.com/Mohit-Kirtane/tracewell"
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-border px-5 py-3 font-display text-[13px] font-medium tracking-wide text-text transition hover:border-signal hover:text-signal"
          >
            VIEW ON GITHUB
          </a>
        </div>

        <p className="mt-5 font-mono text-xs text-text-faint">
          pip install tracewell-sdk · MIT licensed
        </p>
      </div>

      <div className="flex justify-center lg:justify-end">
        <SampleTracePanel />
      </div>
    </section>
  );
}
