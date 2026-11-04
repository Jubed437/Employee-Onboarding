# Architecture

## MVP boundaries

The MVP is an offline-first, deterministic onboarding orchestrator. Core workflow
decisions are made by typed configuration and backend services; an LLM may explain
results later, but it does not decide compliance, approvals, scores, or dates.

## Technology decisions

- **Backend:** Python 3.12, FastAPI, Pydantic v2, and SQLAlchemy 2.x.
- **Database:** SQLite for the MVP, with PostgreSQL-compatible relational models so
  the persistence layer can be migrated without changing domain behaviour.
- **Task graph:** relational task/dependency tables with `networkx` for graph
  calculations. Risk, root-cause, impact, and readiness calculations remain
  deterministic.
- **Configuration:** YAML validated at startup with Pydantic. Adding a profile or
  playbook should not require application code changes.
- **Frontend:** React 18, TypeScript strict mode, and Vite.
- **LLM:** provider-agnostic interface with a deterministic mock and an off switch.

## Deferred capabilities

Embeddings and vector search are intentionally deferred. The MVP's requirements
are structured dependency traversal, date arithmetic, approvals, RBAC, audit
records, and explainable scoring; semantic retrieval does not improve those paths.

If policy search, document classification, or a semantic hire assistant becomes
necessary, embeddings can be introduced behind the LLM/integration boundary. The
first implementation should use a replaceable provider and a small, isolated
retrieval component rather than coupling vector storage to core onboarding tables.

## Operational constraints

- Synthetic personal data only.
- No PII in logs or LLM requests; redact before optional provider calls.
- The application must work with LLM features disabled.
- All business time comes from the clock service, not direct system-clock calls.
- SQLite is a local/demo choice, not a production deployment recommendation.
- Root-cause analysis selects deterministic frontier candidates, preferring
  rejected tasks over blocked tasks when projected finish times tie. Impact
  analysis traverses descendants through dependency edges and aggregates
  projected finish dates and outcome tags.
- Playbook recommendations are simulated and ranked deterministically. Their
  idempotency keys prevent duplicates; AUTO actions execute immediately, while
  approval tiers require the appropriate manager and/or HR approval records.
- Readiness is a deterministic weighted score over critical completion, slack,
  compliance, and timeliness. Each persisted snapshot includes its formula
  components and task-level drivers for explainability.
