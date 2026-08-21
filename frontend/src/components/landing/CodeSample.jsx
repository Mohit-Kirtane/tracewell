const CODE = `from tracewell_sdk import TracewellCallbackHandler

handler = TracewellCallbackHandler(api_key="tw_...")
result = agent.invoke(question, config={"callbacks": [handler]})
handler.finish(status="complete")`;

export function CodeSample() {
  return (
    <section className="mx-auto w-full max-w-5xl px-6 py-20 sm:px-10">
      <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="font-display text-[11px] font-medium tracking-[0.18em] text-signal uppercase">
            The SDK
          </p>
          <h2 className="mt-2 font-display text-2xl font-bold text-text sm:text-3xl">
            Five lines. No new agent framework to learn.
          </h2>
          <p className="mt-4 max-w-md font-body text-sm leading-relaxed text-text-dim">
            <code className="font-mono text-[13px] text-signal">tracewell-sdk</code> is a
            standard LangChain callback handler. It works with any chain, agent, or
            LangGraph graph you already have — no rewrite required.
          </p>
        </div>

        <div className="overflow-x-auto rounded-xl border border-border bg-[#12161f] p-6 shadow-[0_30px_60px_-30px_rgba(15,23,42,0.35)]">
          <pre className="font-mono text-[13px] leading-relaxed text-[#e2e8f0]">
            <code>{CODE}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}
