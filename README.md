# FolioPrior Auth

*A prior authorization multi-agent platform.*

> **DEMONSTRATION SOFTWARE — SYNTHETIC DATA ONLY.** This project shows how a
> multi-agent orchestration architecture, a local RAG pipeline over payer
> policy documents, and an optional LLM can combine to produce explainable,
> auditable prior-authorization determinations. All payer policies and
> patient records included here are synthetic. This is **not** a real
> coverage-determination system, and every response explicitly requires
> sign-off by a qualified clinical reviewer.

## 1. The problem this solves

Prior authorization is one of the most concrete, high-friction problems in
US healthcare: a provider requests a procedure, medication, or piece of
equipment; a payer has to check it against coverage criteria (BMI
thresholds, step-therapy requirements, documentation requirements,
exclusions) before approving it; and delays or opaque denials directly harm
patients waiting on care. This platform models that workflow end-to-end:

1. A structured request comes in (requested service, diagnosis codes,
   urgency, prior treatments already tried) alongside the patient's clinical
   record.
2. The relevant payer policy is retrieved from a local FAISS index — never
   the whole corpus, just the one policy that actually applies.
3. Every individual numbered criterion in that policy is evaluated against
   this specific patient/request as **MET / NOT MET / UNKNOWN**, with the
   evidence used to reach each verdict.
4. A **deterministic rules engine** — not an LLM — turns that criteria
   evaluation into an approve/deny/pend decision, so the actual coverage
   decision stays reproducible and auditable.
5. An LLM (if configured) drafts the natural-language rationale explaining
   that already-computed decision — it never gets to change it.
6. A safety agent independently re-derives what the decision *should* be
   from the same criteria and flags any mismatch, plus verifies every cited
   criterion actually traces back to retrieved policy text.
7. **Every completed determination — approved, denied, or pended — lands in
   a human review queue.** A clinical reviewer either upholds it or
   overrides it with a required rationale before it is final; this is the
   actual mechanism behind `requires_clinician_review`, not just a flag with
   no follow-through (see §12).
8. Everything is persisted to a durable audit trail (every agent's
   input/output, every criterion evaluated, every determination, every
   review decision) and surfaced on an observability dashboard: volume,
   outcomes, per-agent reliability/latency, review-queue throughput and
   override rate, and real LLM token/cost usage.

## 2. Architecture

```text
                  React + TypeScript Frontend (Vite)
        Patients | Policy Search | Observability Dashboard
                            |
                            v  (fetch, CORS-enabled, NDJSON streaming)
                    FastAPI REST API (/api/v1)
                            |
                            v
                 Multi-Orchestration Workflow
                            |
   +------------+-----------+-----------+------------+------------+
   |            |           |           |            |            |
Intake     Retrieval      Risk      Criteria    Determination   Safety
 Agent       Agent        Agent     Matching     Agent (LLM-    Agent
   |            |                    Agent        assisted        |
   |            v                                 rationale)      |
   |      FAISS vector index  <-  Sentence-Transformer embeddings |
   |            |                                                 |
   |      Policy chunks + metadata (SQLite)                       |
   |                                                               |
   +---------------------------------------------------------------+
                            |
                            v
                Final Response Orchestrator
                            |
                            v
      Structured determination + criteria + rationale + disclaimer
                            |
                            v
         SQLite (runs, agent trace, criteria audit trail)
                            |
                            v
                Observability API (/observability/metrics)
```

Routing rules:

- If critical patient fields or required request fields (e.g. diagnosis
  codes) are missing beyond a threshold, the workflow halts right after
  intake and returns a `pended` determination instead of guessing.
- Agent failures (e.g. the vector store being unavailable) never crash the
  run — they're recorded in the trace with `status: "error"` and the
  workflow degrades gracefully, always ending with
  `requires_clinician_review: true`.
- The Determination Agent's decision is **always** derived deterministically
  from the criteria evaluation. The LLM (when configured) only writes the
  rationale text for a decision that has already been made.

## 3. Technology Stack

**Backend**

- Python 3.11+, FastAPI, Pydantic v2, Uvicorn
- SQLAlchemy 2.0 models over SQLite
- FAISS (`IndexFlatIP` on normalized embeddings) + Sentence Transformers
  (`all-MiniLM-L6-v2` by default, configurable)
- Anthropic Claude (optional) for determination-rationale drafting, via the
  official `anthropic` SDK
- A small dependency-free multi-agent framework (`BaseAgent` +
  `ClinicalWorkflowState`) — no external agent framework required
- Pytest, pytest-asyncio, FastAPI `TestClient`

**Frontend**

- React 18 + TypeScript, built with Vite
- React Router for navigation
- Plain `fetch` API client with types mirroring the backend's Pydantic
  schemas — no extra HTTP/state libraries

## 4. Repository Layout

```text
backend/
  app/
    api/            health, patients, guidelines, search, orchestration, review, observability
    core/           settings (incl. LLM config), logging, exception types
    db/             SQLAlchemy models, engine/session, repositories
    schemas/        Pydantic request/response models (incl. review, observability)
    agents/         intake, retrieval, risk, criteria_matching, determination
                     (LLM-assisted), safety - one file each, + BaseAgent
    orchestration/  workflow (routing), state, determination_rules (shared
                     decision logic), final response orchestrator
    rag/            embeddings, chunker, FAISS store, ingestion, retriever
    services/       orchestration_service, review_service (human-in-the-loop),
                     metrics_service, llm_client
    utils/          text cleaning, field validation helpers
  data/
    guidelines/     synthetic PAYER POLICY .txt documents (imaging, bariatric
                     surgery, specialty medication, physical therapy, DME)
    patients/       synthetic patient seed data (sample_patients.json)
  vector_store/     generated FAISS index + metadata sidecar (gitignored)
  scripts/          ingest_guidelines.py, seed_database.py
  tests/            unit + integration tests (fake, offline embeddings)
  requirements.txt, Dockerfile, pytest.ini, .env.example

frontend/
  src/
    api/            typed REST client (client.ts, types.ts)
    agentPipeline.ts live pipeline step definitions + state helpers
    components/     Badge (incl. Determination/Criterion badges), SafetyBanner,
                     AssessmentResult, AgentPipeline, AgentTraceView, PatientForm
    pages/          PatientsPage, PatientDetailPage, GuidelineSearchPage,
                     ReviewQueuePage, ReviewDetailPage, ObservabilityPage
    App.tsx, main.tsx, index.css
  package.json, vite.config.ts, tsconfig.json, Dockerfile, nginx.conf, .env.example

docker-compose.yml  orchestrates both services
```

## 5. Backend: Installation & Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

> Requires internet access the first time you run ingestion, to download the
> `all-MiniLM-L6-v2` embedding model from Hugging Face (cached locally after
> that).

### Enabling real LLM-drafted rationales (optional)

By default both `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are blank and the
Determination Agent uses a deterministic, templated rationale — the platform
is fully functional with zero external dependencies. To see real LLM-generated
rationales and real token/cost metrics on the observability dashboard, set
`LLM_PROVIDER` plus that provider's key in `backend/.env`:

```env
# Anthropic (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# ...or OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Only the selected provider's key needs to be set. The LLM is only ever asked
to phrase a decision the deterministic rules engine already made (see
`backend/app/services/llm_client.py`) — it cannot change an approve/deny/pend
outcome.

### Database & RAG initialization

These two scripts also run automatically and idempotently on API startup,
but you can run them explicitly (from `backend/`):

```bash
python scripts/ingest_guidelines.py   # builds the FAISS index from data/guidelines/*.txt
python scripts/seed_database.py       # seeds 10 synthetic demo patients
```

Both are safe to re-run — they skip work that has already been done. If you
change the guideline corpus, delete `clinical_guidelines.db` and
`vector_store/*` first so they rebuild from scratch.

### Running the API

```bash
cd backend
uvicorn app.main:app --reload
```

- Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>

CORS is enabled for `http://localhost:5173` and `http://localhost:3000` by
default (`CORS_ORIGINS` in `backend/.env.example`).

### Running backend tests

```bash
cd backend
pytest tests/ -v
```

50 tests, fully offline (deterministic hashed-embedding stand-in for the
real model — see `tests/fake_embeddings.py`), covering: patients CRUD,
guideline ingestion/search, every agent in isolation (including two
regression tests for real bugs found via live testing during development —
see §13), the full streaming workflow, the human-in-the-loop review flow
(queue, uphold, override, double-review rejection), and the observability
metrics service.

## 6. Frontend: Installation & Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- App: <http://localhost:5173>
- `VITE_API_BASE_URL` (in `frontend/.env`) — defaults to
  `http://localhost:8000/api/v1`.

Build for production: `npm run build` (outputs to `frontend/dist`), then
`npm run preview`.

### What's in the UI

- **Patients** — list of synthetic patients, a form to add a new one.
- **Patient detail** — demographics/vitals/labs/history, a structured prior
  authorization request form (requested service, category, diagnosis codes,
  urgency, prior treatments tried), and a live multi-agent pipeline that
  lights up step by step as each agent actually completes on the backend,
  with a growing live detail log of each agent's real input/output. The
  final result shows the determination badge (approved/denied/pended), the
  rationale (and whether it was LLM-drafted or templated), every criterion
  evaluated with its MET/NOT_MET/UNKNOWN status and patient-side evidence,
  and the retrieved policy evidence it's all grounded in. A banner links
  straight to that run's entry in the review queue, and a **Download PDF
  report** button (also on the review page) renders that same stored
  determination — criteria, evidence, rationale, and review outcome once
  reviewed — as a downloadable PDF via `GET /orchestration/runs/{id}/report.pdf`
  (server-rendered with ReportLab; it's a rendering of the audit trail, not
  a new computation).
- **Review Queue** — every completed determination awaiting a clinical
  reviewer's sign-off. Click through to uphold or override it (override
  requires picking a final determination and writing a rationale) — the
  full AI response is shown alongside the review form so the reviewer has
  everything needed to decide.
- **Policy Search** — standalone semantic search against the payer policy
  corpus.
- **Observability** — system health, request volume, approve/deny/pend
  breakdown, per-agent latency & reliability, human review queue
  throughput and override rate, real LLM token usage and estimated cost,
  and a recent-requests table.

## 7. Example API Requests

**Run a determination (streaming — what the UI actually uses)**

```bash
curl -N -X POST http://localhost:8000/api/v1/orchestration/run/stream \
  -H "Content-Type: application/json" \
  -d '{
        "patient_id": 4,
        "requested_service": "Bariatric surgery (Roux-en-Y gastric bypass)",
        "service_category": "surgery",
        "diagnosis_codes": ["E66.01 - morbid obesity"],
        "prior_treatments_tried": ["supervised weight-management program for 6 months", "nutrition counseling"]
      }'
```

Streams one JSON line per agent, then a final line:

```json
{"type": "agent", "agent": "clinical_intake_agent", "status": "success", "execution_time_ms": 0.03, ...}
{"type": "agent", "agent": "guideline_retrieval_agent", "status": "success", "execution_time_ms": 15.06, ...}
{"type": "agent", "agent": "risk_stratification_agent", "status": "success", "execution_time_ms": 0.03, ...}
{"type": "agent", "agent": "criteria_matching_agent", "status": "success", "execution_time_ms": 0.23, ...}
{"type": "agent", "agent": "determination_agent", "status": "success", "execution_time_ms": 0.31, ...}
{"type": "agent", "agent": "safety_validation_agent", "status": "success", "execution_time_ms": 0.03, ...}
{"type": "final", "run_id": 1, "determination": "approved", "decision_rationale": "...", "criteria_evaluated": [...], ...}
```

**Check observability metrics**

```bash
curl http://localhost:8000/api/v1/observability/metrics
```

```json
{
  "health": { "database": "UP", "vector_store": "UP", "llm_configured": false },
  "total_requests": 6,
  "determination_breakdown": { "approved": 1, "denied": 2, "pended": 3, "total": 6 },
  "requires_clinician_review_rate": 1.0,
  "agent_stats": [{ "agent": "clinical_intake_agent", "total_calls": 6, "avg_execution_time_ms": 0.03, ... }],
  "llm_usage": { "enabled": false, "total_calls": 0, "fallback_count": 6, "estimated_cost_usd": 0.0 }
}
```

## 8. Docker (both services)

```bash
docker compose up --build
```

- Backend: <http://localhost:8000> (Swagger at `/docs`)
- Frontend: <http://localhost:3000>

Pass `LLM_PROVIDER` and the matching `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
as environment variables to the `backend` service in `docker-compose.yml` to
enable real LLM rationales in the containerized deployment too.

## 9. Multi-Agent Workflow

| Agent | Responsibility |
|---|---|
| `clinical_intake_agent` | Computes BMI if missing, validates required patient fields *and* request fields (e.g. diagnosis codes), extracts human-readable facts |
| `guideline_retrieval_agent` | Builds a retrieval query from the requested service + diagnoses + prior treatments, searches FAISS, filters low-relevance hits |
| `risk_stratification_agent` | Deterministic clinical risk classification (BP, lipids, glycemic status, BMI, smoking, cardiovascular history) feeding into context |
| `criteria_matching_agent` | Extracts every individual numbered criterion from the **single most relevant** retrieved policy and evaluates it MET/NOT_MET/UNKNOWN against this request — numeric criteria (e.g. BMI bands) are checked exactly against patient data; documentation/step-therapy criteria against what was actually submitted |
| `determination_agent` | Deterministically decides approve/deny/pend from the criteria evaluation, then (optionally) asks Claude to draft the rationale for that already-made decision, tracking real token usage |
| `safety_validation_agent` | Independently re-derives the expected determination from the same criteria and flags any mismatch; verifies every cited criterion traces back to retrieved text; flags missing info and high risk |

The `FinalResponseOrchestrator` (`backend/app/orchestration/orchestrator.py`)
runs this pipeline via `ClinicalWorkflow`
(`backend/app/orchestration/workflow.py`); the actual decision rule lives in
`backend/app/orchestration/determination_rules.py` and is shared by the
determination and safety agents so they can never silently disagree.

## 10. RAG Architecture

1. **Chunking** (`chunker.py`): policy `.txt` files are parsed by `SECTION:`
   headers, then split into ≤600-character sentence-aligned sub-chunks.
2. **Embedding** (`embeddings.py`): a lazily loaded, cached
   Sentence-Transformers model, L2-normalized.
3. **Indexing** (`faiss_store.py`): `faiss.IndexFlatIP` on normalized vectors
   (= cosine similarity) with a JSON metadata sidecar.
4. **Retrieval** (`retriever.py`): results below `MIN_RELEVANCE_SCORE`
   (0.15) are discarded as not sufficiently relevant.
5. **Dominant-policy restriction** (`criteria_matching_agent.py`): a request
   is evaluated against the **one** policy whose best-matching chunk scored
   highest — not every policy that scored above the retrieval threshold —
   mirroring how a real request is only ever evaluated against the one
   applicable payer policy.

## 11. Observability & Value Metrics

`GET /api/v1/observability/metrics` (dashboard: the **Observability** tab)
aggregates directly from the same `orchestration_runs` / `agent_outputs`
audit trail every run already writes to — no separate metrics store. Accepts
`?period=7d|30d|month|year|all` (default `all`) to scope every section below
to a trailing window instead of full history; the dashboard exposes this as a
dropdown next to the page title.

- **Health**: database, vector store, and LLM-configured status (including
  which provider — `anthropic` or `openai` — is selected).
- **Volume & value**: total/completed/pended request counts, average
  end-to-end latency, the clinician-review-rate (always 100% by design —
  a useful compliance sanity check), and the approve/deny/pend breakdown.
- **Per-agent reliability & latency**: call count, success/error count,
  average and p95 execution time, per agent.
- **LLM usage & cost**: when an LLM provider is configured (`ANTHROPIC_API_KEY`
  or `OPENAI_API_KEY`, per `LLM_PROVIDER`), real per-call input/output token
  counts (straight from the provider's API response `usage` field), total
  tokens, an *illustrative* estimated cost (configurable $/1M-token rates —
  not billing-accurate), and how many runs fell back to the deterministic
  template (LLM disabled or a call failed). `GET /api/v1/observability/costs`
  (the **Cost per execution** card) separately filters LLM spend by
  `period=7d|30d|month|year|custom`.
- **Recent requests**: the last 20 runs (within the selected period) with
  their outcome.

### Chart-based insights

The dashboard renders this as actual charts, not just numbers, chosen by
data job rather than by taste (`frontend/src/charts/`):

- **Determination outcomes** and **reviewer decisions** — a single
  horizontal stacked bar per breakdown (`StackedOutcomeBar.tsx`), not a
  pie/donut: these are 2-3-slice part-to-whole status breakdowns, and a
  stacked bar reads magnitude and share at a glance without the decoding
  pie slices require. Hand-built with real hover/focus tooltips, a 2px
  surface gap between segments, and a persistent legend.
- **Per-agent latency (avg vs. p95)** — a grouped bar chart (Recharts,
  `AgentLatencyChart.tsx`) on a **log scale**, because the retrieval
  agent's embedding call can be three orders of magnitude slower than the
  other agents on a cold start; a linear axis would flatten every other
  agent to an invisible sliver. Avg/p95 are two non-state measurements, so
  they use the fixed-order **categorical** palette (not status colors).
- **Per-agent reliability** — a stacked bar of success vs. error counts per
  agent. Success/error *is* a state, so it wears the reserved **status**
  colors (good/critical), never the categorical theme — the "collision
  rule": a series that means good/bad wears status tokens, a series that's
  just "series 4" wears categorical, never both in one chart.
- Every chart color traces back to a validated palette
  (`frontend/src/charts/colors.ts`, sourced from the project's dataviz
  skill) — checked for CVD-safe separation and contrast with
  `validate_palette.js` rather than eyeballed, and the underlying numeric
  table stays visible beside every chart so nothing is chart-gated.

## 12. Human-in-the-Loop Review

`requires_clinician_review` isn't just a flag in a JSON response — it's a
real, enforced workflow. Every completed determination (approved, denied,
*or* pended) lands in a durable review queue, and nothing is truly final
until a human has acted on it:

1. **Queue** (`GET /api/v1/review/queue`, UI: **Review Queue**) — every run
   with `review_status = pending_review`, oldest first: patient, requested
   service, the AI's determination, and urgency.
2. **Detail** (`GET /api/v1/review/{run_id}`) — the complete AI response
   (summary, criteria evaluated, evidence, rationale, safety flags) exactly
   as it was produced, stored verbatim in `final_response_json` at
   completion time so the review always reflects what the reviewer actually
   saw.
3. **Decision** (`POST /api/v1/review/{run_id}`) — a reviewer either:
   - **Uphold**s the AI determination as-is, or
   - **Override**s it with a *required* `final_determination` and a
     *required* rationale note (enforced server-side — you cannot override
     silently).

   Either way the decision is durably recorded (`reviewer_name`,
   `reviewer_decision`, `final_determination`, `reviewer_notes`,
   `reviewed_at`) and the run is removed from the queue exactly once — a
   second review attempt on the same run is rejected (`400`).
4. **Observability** — the dashboard's "Human-in-the-loop review" panel
   shows pending count, reviewed count, upheld vs. overridden counts, the
   **override rate** (how often a human actually disagreed with the AI —
   a key trust metric for this kind of system), and average time-to-review.

This is deliberately a *separate* dimension from the AI's own processing
`status` (`completed` / `insufficient_information`): `status` describes
whether the agent pipeline finished, `review_status` describes whether a
human has signed off. A `pended` AI outcome still goes through the exact
same human review gate as an `approved` or `denied` one, because a pend
usually means "a human needs to look at this," which is exactly what the
queue is for.

## 13. Safety Considerations & real bugs found via live testing

This system was iterated against live, real requests during development —
not just unit tests — which surfaced two real correctness bugs, fixed and
now covered by regression tests:

1. **Alternative criteria bands**: a policy's BMI criteria are alternative
   qualifying pathways ("BMI ≥ 40" *or* "BMI 35–39.9 with a comorbidity"),
   not a checklist every band must pass. The determination logic now treats
   failing one BMI band as a non-blocker when another band is met
   (`determination_rules.blocking_not_met_criteria`).
2. **Negated exclusion criteria**: criteria phrased as negations ("requests
   *without* documented improvement are not necessary") can't have their
   truth value reliably resolved by lexical overlap alone — guessing wrong
   means confidently *denying* care that should have been approved. This
   tier now only ever flags `UNKNOWN` (pend for human review), never
   `NOT_MET`, when it can't be sure.

Other safety properties by design:

- All policy text is explicitly synthetic and labeled
  `STATUS: DEMONSTRATION DATA` — never a real payer policy.
- The coverage decision is always computed deterministically; the LLM (when
  used) only drafts the explanation for a decision already made.
- The safety agent independently re-derives the expected determination and
  flags any mismatch, and verifies every cited criterion is actually present
  in retrieved text.
- `requires_clinician_review` is always `true`; every response carries a
  safety disclaimer.
- The workflow pends (rather than guessing) when critical information is
  missing.

## 14. Limitations

- The criteria-matching heuristic is lexical (token-overlap plus a few
  hand-written rule tiers for BMI/step-therapy/exclusion patterns), not a
  full clinical-NLP or logic-graph engine — it can still produce
  low-confidence `UNKNOWN` verdicts on ambiguous phrasing, by design routed
  to human review rather than guessed.
- Retrieval quality depends on the small, synthetic policy corpus included
  here (5 documents); not representative of real payer policy coverage or
  volume.
- No real payer integration (X12 278, FHIR PriorAuth, etc.) — this is a
  decision-support demonstration, not a claims/EDI system.
- No authentication/authorization layer — not intended for exposure beyond
  a local/demo environment.
- LLM cost estimates use configurable illustrative rates, not live pricing.
- The frontend has no automated test suite in this iteration (backend has
  full unit/integration coverage, including regression tests for the two
  bugs above).

## 15. Future Enhancements

- A logic-aware criteria model (explicit AND/OR grouping between criteria)
  instead of the alternative-band special case.
- Multi-hop reasoning that can resolve negation and conditional criteria
  more precisely than lexical overlap.
- Additional payer policy corpora and configurable embedding models.
- Role-based access control, audit logging, and multi-tenant isolation for
  a real multi-payer/multi-provider deployment.
- Frontend component/E2E tests (Vitest + Testing Library, Playwright).
- Streaming token-by-token display of the LLM-drafted rationale as it's
  generated, in addition to the per-agent pipeline streaming already in
  place.
