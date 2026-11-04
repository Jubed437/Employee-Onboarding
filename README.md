# Employee Onboarding Orchestrator

An offline-first employee onboarding orchestration application built in stages from the [product requirements document](docs/PRD.md).

## Architecture decisions

The MVP uses SQLite through SQLAlchemy with a PostgreSQL-compatible relational
schema. Task dependencies and risk calculations are deterministic; embeddings
and vector search are deliberately deferred until a measured semantic-search
requirement exists. See the [architecture overview](docs/architecture.md) and
[ADR-001](docs/decisions/ADR-001-mvp-storage-and-search.md).

Plan generation is configuration-driven: employee profile variants produce a
deterministic task graph, business-day due dates, dependency rows, and initial
task states. Re-running generation for an employee is idempotent.

Task transitions are enforced by a service-level state machine. Successful
transitions append event and audit records, enforce actor permissions, and
unlock dependent tasks when their prerequisites are complete.

The API exposes demo persona login and JWT-protected hire and task operations
under `/api/v1`. Set `JWT_SECRET` to a strong environment value outside local
development; the built-in secret is for the synthetic demo only.

Risk evaluation is deterministic and configuration-driven: open tasks receive
earliest-finish and slack calculations, with explicit reasons for overdue work,
upstream delay, rework, owner overload, external SLAs, and critical gates.

Root-cause analysis identifies the highest-priority blocked or rejected task
frontier and returns its dependency chain. Downstream impact analysis traverses
dependent tasks and summarizes affected projected outcomes and outcome tags.

Playbook recommendations are configuration-driven and deterministic. Matching
actions are ranked by breach resolution, approval tier, and disruption, persisted
idempotently, and auto-tier actions execute immediately. Approval-tier actions
require the configured manager/HR approvals before their effects are applied.

Readiness snapshots combine critical completion, projected slack, compliance, and
timeliness using the configured weights and expose the component breakdown,
band, and deterministic task drivers.

Stage 10 adds the synchronous monitor boundary, simulation endpoints
(`/api/v1/sim/*`), a notification outbox mock, and an authenticated SSE stream
at `/api/v1/stream`. Seed the synthetic demo data with `make seed`.

The Stage 11 frontend provides a responsive app shell with synthetic persona
login, persisted JWT auth, role-filtered navigation, simulated-time status,
SSE connectivity, and reusable status, score, progress, loading, empty, and
error components.

Stage 12 adds the active-hires table, validated new-hire form, readiness
snapshot endpoints, and a hire Overview with score band, formula breakdown,
and deterministic readiness drivers.

Stage 13 adds plan and owner-queue APIs plus the frontend task plan, state
filters, role-aware task drawer actions, owner queue, and new-hire checklist.

Stage 14 adds open-risk and recommendation approval APIs, a dependency graph
view, risk cards with root-cause/impact details, and manager/HR approval actions.

## Local development

Backend prerequisites: Python 3.12+.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e "backend[dev]"
alembic -c alembic.ini upgrade head
python -m uvicorn app.main:app --app-dir backend --reload
```

The API is available at `http://localhost:8000`, with a health check at `/health`.

Install frontend dependencies and start Vite in a second terminal:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

Run checks from the repository root:

```powershell
make test
make lint
make frontend-build
make db-upgrade
```
