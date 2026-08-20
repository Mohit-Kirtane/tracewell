# Tracewell — Design Spec

Date: 2026-08-20
Status: Approved for implementation planning

## 1. Purpose

A hosted observability and evaluation tool for LLM agents. A developer drops a
LangChain/LangGraph callback handler into their own app; every LLM call, tool
call, and retrieval step streams into Tracewell as a trace; each project can
define custom LLM-judge evaluators that automatically score completed traces
in the background. Multi-tenant, with real accounts and per-project API keys
— the same shape as LangSmith or Langfuse, scoped down to a buildable size.

This is a portfolio project, built to demonstrate a skill distinct from
Dossier (the author's existing RAG/agent platform): agent testing and
observability, rather than another agent application. It is deliberately a
*generic, reusable tool* — usable by anyone's LangChain app, not just the
author's — and Dossier itself will be wired up as the first real, live
integration proof.

## 2. Non-goals (explicitly out of scope for v1)

- Golden-dataset / regression testing (re-running a fixed test set to catch
  regressions). Real candidate for v2.
- Team accounts or sharing a project between multiple users.
- Alerting or notifications on scores/errors.
- Support for non-LangChain instrumentation (a generic `@traced` decorator
  for arbitrary Python code is a possible v2 add-on to the SDK).
- Cost budgets, spend limits, or billing of any kind.
- Full-text search over trace content — v1 filtering is by project, status,
  and date only.

## 3. Tech stack

- **Backend**: FastAPI (Python) — same framework as Dossier, for velocity.
- **Database**: MongoDB — a deliberate change from Dossier's Postgres.
  Traces are a tree of variable-shaped span documents (an LLM-call span has
  different fields than a tool-call or retrieval span); a document store is
  a better structural fit than forcing this into relational tables, and it
  closes a real gap: the author's resume already claims MongoDB experience
  for the Enterprise Knowledge Copilot project, but Dossier's actual
  implementation never used it.
- **Frontend**: React + Vite + Tailwind — same approach as Dossier.
- **LLM judge**: Gemini via the OpenAI-compatible endpoint, same pattern
  (and same two-key `.with_fallbacks()` trick for free-tier quota) as
  Dossier's `app/core/llm.py`.
- **Deployment**: Render (API + a second background-worker service) +
  MongoDB Atlas free tier, mirroring Dossier's Render + Neon pattern.

## 4. Data model (MongoDB collections)

- **`users`** — `email`, `password_hash`, `created_at`. Same auth pattern as
  Dossier (bcrypt + JWT cookie).
- **`projects`** — `user_id`, `name`, `created_at`. A workspace; traces,
  API keys, and evaluators are scoped to a project.
- **`api_keys`** — `project_id`, `key_hash`, `key_prefix` (shown once at
  creation, like a GitHub PAT), `created_at`, `revoked_at`. Used to
  authenticate SDK ingestion calls — never the user's JWT.
- **`traces`** — one document per agent run:
  - `project_id`, `name`, `status` (`running` | `complete` | `error`)
  - `started_at`, `ended_at`
  - `total_tokens`, `total_cost_estimate` (rolled up from spans)
  - `spans`: embedded array, each span has `id`, `parent_id` (for
    reconstructing the call tree), `type` (`llm` | `tool` | `retriever` |
    `chain`), `name`, `input`, `output`, `started_at`, `ended_at`,
    `tokens`, `error` (nullable)
- **`evaluators`** — `project_id`, `name`, `judge_prompt_template`,
  `score_scale` (e.g. 1-5, or pass/fail), `active` (bool), `created_at`.
- **`evaluations`** — one document per (`trace_id`, `evaluator_id`) pair:
  `score`, `reasoning` (the judge's explanation text), `status`
  (`pending` | `done` | `failed`), `created_at`.

Spans are embedded in their trace document (not a separate collection) so
that rendering one trace's full waterfall is a single read — the natural
MongoDB shape for this access pattern.

## 5. API surface

**Ingestion API** (authenticated via `Authorization: Bearer <api_key>`,
*not* the user JWT):
- `POST /api/v1/traces` — start a new trace; returns its id.
- `PATCH /api/v1/traces/{id}` — append spans and/or update status as the
  run progresses; the SDK calls this as each span completes and once more
  to mark the trace `complete` or `error`.

**Dashboard API** (authenticated via the user's JWT cookie, same pattern as
Dossier's `get_current_user` dependency):
- `POST/GET /api/projects` — create/list the user's projects.
- `POST/GET/DELETE /api/projects/{id}/api-keys` — create (returned once),
  list (prefix only), revoke.
- `GET /api/projects/{id}/traces` — list, filtered by status/date.
- `GET /api/traces/{id}` — one trace, full span tree + its evaluations.
- `POST/GET/PATCH /api/projects/{id}/evaluators` — create/list/edit.
- `POST /api/traces/{id}/rescore` — manually re-run active evaluators
  against one trace (for when an evaluator is added after the fact).

## 6. SDK (`tracewell-sdk`)

A small, independently-installable Python package containing
`TracewellCallbackHandler(BaseCallbackHandler)`. It hooks LangChain's
`on_llm_start/end`, `on_tool_start/end`, `on_retriever_start/end`, and
`on_chain_start/end` callbacks, buffers them into spans client-side, and
calls the ingestion API. Usage is one line:

```python
from tracewell_sdk import TracewellCallbackHandler

handler = TracewellCallbackHandler(api_key="tw_...", project="my-agent")
agent.invoke(question, config={"callbacks": [handler]})
```

The SDK ships as its own package (own `pyproject.toml`) inside this repo,
publishable to PyPI, so it is genuinely usable by someone else's project —
not just a folder that only works from within Tracewell's own codebase.
Dossier will be wired up as the first live integration, proving the SDK
works against a real, already-deployed LangGraph app.

## 7. Background scoring worker

A simple polling process — no queue broker needed at this scale. Every few
seconds it queries MongoDB for traces with `status: "complete"` that have
at least one `active` evaluator with no corresponding `evaluations`
document, runs that evaluator's judge prompt against the trace's spans via
the LLM, and writes the resulting `evaluations` document. Deployed as a
second Render service from the same container image, with a different
start command (`python -m app.worker` instead of `uvicorn app.main:app`).

## 8. Frontend / dashboard

- Login / register — same visual pattern as Dossier's auth pages.
- Project switcher + "new project."
- Trace list — filterable table (status, date, name), showing rolled-up
  cost/tokens and evaluator score badges per row.
- Trace detail — a waterfall/tree view of spans (name, type, duration,
  input/output preview, expandable), with evaluation scores and judge
  reasoning shown alongside. This view has no equivalent in Dossier — it's
  the one genuinely new frontend skill this project adds to the portfolio.
- Evaluators page (per project) — create/edit a named judge prompt.
- API keys page (per project) — generate/revoke, key shown once.

## 9. Testing approach

Following the same discipline that caught real bugs in Dossier:
- Node/state-shape and background-worker logic get workflow-level tests
  that exercise the real code path end to end, not just unit tests of
  individual functions in isolation — this is what caught the LangGraph
  node/state-key collision bug in Dossier that node-level tests missed.
- Before any deploy-affecting change, a smoke test against the real
  MongoDB Atlas instance (mirroring the Postgres FK-ordering bug Dossier's
  seed script hit only against real Postgres, never against SQLite).
- The SDK gets its own test suite independent of the API, using a fake
  HTTP transport, so it can be verified without a live server.

## 10. Open questions for implementation planning

None outstanding — all major decisions were settled during brainstorming
(see the approved options above). Naming/branding polish (colors, type,
landing page identity) is deferred to a design pass once the product
itself works, matching how Dossier's visual identity came after the
functional MVP.
