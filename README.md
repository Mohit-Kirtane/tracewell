# Tracewell

A hosted observability and evaluation tool for LangChain/LangGraph agents.
Drop a callback handler into your agent, watch every LLM call, tool call, and
retrieval step show up as a trace, and define custom LLM-judge evaluators
that automatically score completed runs in the background.

Built as a companion project to [Dossier](https://github.com/Mohit-Kirtane/dossier)
(an enterprise RAG/agent platform) — deliberately a different kind of
project: agent *testing and observability*, not another agent application.
Dossier is wired up to Tracewell as the first real integration, tracing its
own document-intelligence workflow live.

## What it does

- **Trace** — a small Python SDK (`tracewell-sdk`) ships a LangChain
  `BaseCallbackHandler`. Attach it to any chain or graph and every step gets
  recorded: what kind of step it was (LLM call, tool call, retrieval,
  chain), what went in, what came out, how long it took, and how it nests
  under its parent step.
- **View** — a dashboard renders each trace as a proportional waterfall —
  timeline bars sized by actual duration, not just an indented list —
  click any span to see its full input/output.
- **Evaluate** — define one or more evaluators per project: a name and a
  judge prompt ("Is the answer grounded in the retrieved context? Score
  1-5."). A background worker scores every completed trace against every
  active evaluator automatically, using an LLM as the judge, and records
  the score plus its reasoning. Failures (e.g. the judge API is down) are
  recorded as `failed` with the real error, not silently dropped.
- **Multi-tenant** — real accounts, projects, and per-project API keys
  (shown once at creation, hashed at rest) — the same shape as hosted tools
  like LangSmith or Langfuse, scoped down to something one person can
  build and operate.

## Architecture

```
tracewell-sdk (your agent process)
  -> POST/PATCH /api/v1/traces   (API-key authenticated)
       -> MongoDB: traces (with embedded spans)

Dashboard (React)
  -> /api/projects, /api/projects/{id}/traces, /api/traces/{id}, ...
       (user-JWT authenticated, same bcrypt+cookie pattern as Dossier)

Background worker (separate process)
  -> polls MongoDB for complete traces missing an evaluation
  -> runs the judge LLM against each active evaluator's prompt
  -> writes back a score + reasoning, or "failed" + the real error
```

Traces are stored in MongoDB with spans embedded directly in the trace
document — a trace is naturally a tree of variable-shaped events (an LLM
span has different fields than a tool-call or retrieval span), which is a
better fit for a document store than forcing it into relational tables.
Fetching one trace's full waterfall is a single read.

Tracing is treated as best-effort everywhere it touches a host app: SDK
construction failures, network errors, and finishing calls are all caught
and swallowed on the host-app side (see Dossier's integration) — a broken
or unreachable Tracewell instance must never be able to take down the app
it's observing.

## Using the SDK

```python
from tracewell_sdk import TracewellCallbackHandler

handler = TracewellCallbackHandler(api_key="tw_...", base_url="https://your-tracewell-instance")
result = agent.invoke(question, config={"callbacks": [handler]})
handler.finish(status="complete")
```

Install straight from this repo until it's published to PyPI:

```bash
pip install "tracewell-sdk @ git+https://github.com/Mohit-Kirtane/tracewell.git#subdirectory=sdk"
```

## Running locally

Backend:

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
# edit .env: point MONGODB_URI at a local MongoDB or a free MongoDB Atlas
# cluster (https://www.mongodb.com/cloud/atlas/register), and set
# LLM_API_KEY (https://aistudio.google.com/apikey) for the judge
uvicorn app.main:app --reload --port 8000
```

Background worker (separate terminal, same `.env`):

```bash
cd backend
python -m app.worker
```

Frontend (separate terminal) — dev server proxies `/api` to the backend on
port 8000:

```bash
cd frontend
npm install
npm run dev
```

Register an account, create a project, generate an API key, then send a
trace from any LangChain app using `tracewell-sdk` — it shows up in the
dashboard within seconds, and gets a judge score within one worker poll
interval of being marked complete.

### Tests

```bash
cd backend && pytest       # 44+ tests, MongoDB mocked with mongomock-motor
cd sdk && pytest           # SDK tests, HTTP mocked with httpx.MockTransport
```

## Deployment

Single Docker image serves both the API and the built React dashboard
(same pattern as Dossier), plus a second Render service running the
background worker from the same image. [`render.yaml`](render.yaml)
defines both.

1. Create a free MongoDB Atlas cluster (M0 tier) and copy its connection string.
2. On Render: **New → Blueprint**, point it at this repo — it provisions
   both the `tracewell-api` web service and the `tracewell-worker`
   background worker from `render.yaml`.
3. Fill in the `sync: false` env vars on both services: `MONGODB_URI`
   (from Atlas) and `LLM_API_KEY` (from
   [Google AI Studio](https://aistudio.google.com/apikey)). `JWT_SECRET`
   is auto-generated.
4. Deploy.

No PyTorch, no local embedding model, no GPU-sized image — Tracewell has
no retrieval component, so the image stays small without the multi-stage
trimming Dossier's Dockerfile needs.

## Roadmap

Deliberately out of scope for v1 (see the [design spec](docs/superpowers/specs/2026-08-20-tracewell-design.md)
for the full reasoning): golden-dataset/regression testing, team accounts,
alerting, non-LangChain instrumentation, cost budgets, full-text search.

## License

MIT
