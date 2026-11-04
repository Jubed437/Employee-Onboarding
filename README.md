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
