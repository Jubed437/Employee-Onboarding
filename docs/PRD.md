# PRD: Onboarding Orchestrator

*Build specification for a coding agent (Amazon Q or similar) and the team. Scope: India full-time hire MVP. Stack: Python (FastAPI) + React (TypeScript). Hackathon use case 3 (Employee Onboarding).*

## 0. How to use this document (instructions to the coding agent)

1. **Build one stage at a time** (see Section 12). Do not implement features from later stages.
2. Before coding a stage, re-read the sections that stage references. This PRD is the source of truth. If it is ambiguous, choose the simplest option, record it in `docs/decisions/ADR-NNN-title.md`, and list it in your final message.
3. Every stage ends with: tests passing, lint and type checks passing, docs updated, and a list of suggested commit messages.
4. **Commit small.** One logical change per commit, using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).
5. **Never read the system clock directly.** No `datetime.now()` or `Date.now()` in business logic. All time comes from the `Clock` service (Section 7.1).
6. **The LLM never decides compliance, approvals, scores or dates.** Deterministic code does. All LLM calls go through `LLMService` with a non-LLM fallback (Section 7.10).
7. Use only **synthetic personal data**. Never include real names, IDs or bank numbers.
8. Use strict typing: Python type hints checked by `mypy`, TypeScript `strict: true`.
9. Do not add a dependency without stating why in the commit message.
10. Keep modules small and single-purpose. Business logic lives in `services/`, never in API routers or React components.

## 1. Product overview

### 1.1 Problem

Onboarding spans HR, IT, Payroll, Benefits, Learning and the hiring manager. Tasks depend on each other and owners work in silos, so failures are found late (for example, a rejected bank proof is discovered after payroll cutoff and the new hire misses the first salary).

### 1.2 Solution

An onboarding orchestrator that (a) generates a personalized, compliance-aware task plan from the worker profile and location, (b) coordinates department work, and (c) continuously monitors for delay: predicting risk before it happens, explaining the root cause, mapping downstream impact, recommending a recovery action, and executing it after the right approval. A transparent readiness score summarizes the state.

**Design principle:** rules decide, AI explains, humans approve critical actions.

### 1.3 Goals (MVP)

- Generate a correct task graph for an India full-time hire, with variants (fresher or experienced, office or remote, work state).
- Track task state with a strict state machine and an append-only event log.
- Detect delay risk early using slack calculation; produce root cause and downstream impact.
- Recommend recovery actions from a predefined playbook library, with approval tiers and idempotent execution.
- Compute an explainable readiness score.
- Role-based UI for new hire, manager, HR, department owners and admin.
- A simulated clock and failure injection so the demo is repeatable.

### 1.4 Non-goals (MVP)

- Real integrations with Dayforce or any HRIS, payroll or insurer.
- Real document verification, real identity data, real email sending.
- Machine-learning risk models.
- More than one fully built country profile (a small US stub config proves extensibility).
- Mobile apps, i18n, SSO.

### 1.5 Success criteria

- Scenario A and Scenario B (Section 10) run end to end in the UI with the expected outputs.
- Adding a new profile requires only config changes (demonstrated by the stub profile).
- App works fully with the LLM disabled.
- `docker compose up` starts everything and `make seed` loads demo data.

## 2. Roles and permissions

Roles: `NEW_HIRE`, `MANAGER`, `HR`, `PAYROLL`, `IT`, `BENEFITS`, `ADMIN`. (Task owner roles additionally include `LEARNING` and `FACILITIES`, which map to the HR and IT user groups in the demo.)

| Capability | NEW\_HIRE | MANAGER | HR | PAYROLL / IT / BENEFITS | ADMIN |
| --- | --- | --- | --- | --- | --- |
| See own plan and tasks | yes | n/a | n/a | n/a | yes |
| See any hire overview and graph | no | own team | all | only hires with tasks they own | all |
| Update own tasks (start, complete, upload) | yes | yes | yes | yes | yes |
| Reject a submission (verifier) | no | no | yes | yes (own domain) | yes |
| See risks and recommendations | no | own team | all | own domain | all |
| Approve or reject recommendations | no | yes (own team, MANAGER tier) | yes (HR tier) | no | yes |
| Reveal masked PII (audited) | no | no | yes | PAYROLL only | yes |
| Create hire | no | yes | yes | no | yes |
| Simulation controls and config viewer | no | no | no | no | yes |
| View audit log | no | own team | all | own domain | all |

**Auth (MVP):** a persona picker on `/login` issues a signed JWT containing `userId`, `role` and `teamId`. The backend enforces roles via a FastAPI dependency (`require_roles(...)`) and filters data by ownership. This is demo authentication, documented as such.

## 3. Repository structure

```
onboarding-orchestrator/
  README.md
  AGENTS.md                      # copy of Section 0 rules for the coding agent
  docs/
    PRD.md                       # this document (exported as Markdown)
    architecture.md
    decisions/                   # ADRs
  config/
    profiles/india_full_time.yaml
    profiles/us_full_time.yaml   # stub, few tasks
    playbooks.yaml
    scoring.yaml
    policies.yaml                # buffers, rework days, approval tiers
    holidays_in.yaml
  backend/
    pyproject.toml
    app/
      main.py
      core/        config.py clock.py security.py logging.py errors.py
      domain/      enums.py models.py schemas.py
      db/          session.py migrations/
      services/    plan_generator.py state_machine.py event_bus.py audit.py
                   monitor.py risk.py root_cause.py impact.py playbooks.py
                   recommender.py executor.py readiness.py
      integrations/ ports.py mock/ (hris.py it.py payroll.py benefits.py bgv.py learning.py notifier.py)
      llm/         service.py mock.py provider.py redaction.py prompts/
      api/         deps.py routers/ (auth hires tasks risks recommendations readiness sim audit config stream)
    tests/         unit/ scenarios/ conftest.py
    scripts/       seed.py
  frontend/
    package.json
    src/
      api/         generated types + client
      auth/  components/  features/  routes/  lib/  styles/
  docker-compose.yml
  Makefile
  .github/workflows/ci.yml
```

## 4. Tech stack

**Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x with Alembic, SQLite for the MVP (PostgreSQL-compatible schema), `networkx` (graph algorithms), PyYAML, `python-jose` or `pyjwt` (tokens), `sse-starlette` (server-sent events), `pytest`, `ruff`, `mypy`.

**Frontend:** React 18 + TypeScript (strict), Vite, React Router, TanStack Query, Tailwind CSS, shadcn/ui, React Flow plus `dagre` (graph layout), Recharts, `openapi-typescript` (generate API types from the FastAPI schema), Vitest + React Testing Library, Playwright (one e2e test).

**Tooling:** Docker Compose, Makefile (`make dev`, `make test`, `make seed`, `make lint`, `make types`), GitHub Actions CI (lint, type check, tests for both apps).

**LLM:** provider-agnostic `LLMService` interface; provider chosen by env var `LLM_PROVIDER` (`mock` default, or a real provider). Structured JSON outputs validated by Pydantic.

## 5. Domain model

All IDs are UUID strings. All timestamps are timezone-aware, stored in UTC, displayed in `Asia/Kolkata`.

### 5.1 Enums

- `Role`: NEW\_HIRE, MANAGER, HR, PAYROLL, IT, BENEFITS, LEARNING, FACILITIES, ADMIN
- `TaskState`: NOT\_STARTED, READY, IN\_PROGRESS, BLOCKED, REJECTED, DONE, SKIPPED. (**Overdue is a derived flag**, not a stored state: `now > due_date and state not in (DONE, SKIPPED)`.)
- `RiskLevel`: LOW, MEDIUM, HIGH. `RiskStatus`: OPEN, RESOLVED.
- `ReasonCode`: UPSTREAM\_DELAY, REJECTED\_ANCESTOR, OWNER\_OVERLOAD, EXTERNAL\_SLA, CRITICAL\_GATE, OVERDUE
- `ActionType`: SEND\_REMINDER, CREATE\_FOLLOWUP, REASSIGN, EXPEDITE\_EXTERNAL, OFFCYCLE\_PAYROLL, SHIFT\_JOIN\_DATE, EXPRESS\_SHIPPING
- `Tier`: AUTO, MANAGER\_APPROVAL, MANAGER\_AND\_HR\_APPROVAL
- `RecStatus`: PROPOSED, APPROVED, REJECTED, EXECUTED, FAILED, SUPERSEDED

### 5.2 Tables

**employee**: id, full\_name, email, profile\_key (e.g. india\_full\_time), is\_experienced (bool), is\_remote (bool), work\_state (string), job\_title, department, join\_date (date), payroll\_cutoff\_date (date, derived at creation), manager\_id, status (ACTIVE, COMPLETED), created\_at.

**user**: id, display\_name, role, team\_id, employee\_id (nullable, for NEW\_HIRE users).

**task\_instance**: id, employee\_id, template\_key (e.g. PAY-02), title, owner\_role, assignee\_user\_id (nullable), state, due\_date, duration\_days (float), started\_at, completed\_at, attempts (int), rework\_count (int), is\_critical (bool), is\_mandatory (bool), is\_compliance (bool), external\_sla\_days (nullable), outcome\_tags (json list), meta (json, for example rejection reason).

**task\_dependency**: task\_id, depends\_on\_task\_id (composite key). Cycles are rejected at plan generation.

**event\_log** (append-only): id, ts, employee\_id, task\_id (nullable), type, actor (user id or SYSTEM), payload (json).

**risk**: id, employee\_id, task\_id, level, reason\_codes (json), predicted\_breach\_date, slack\_days, root\_cause\_task\_id, impact (json), status, first\_seen\_at, resolved\_at.

**recommendation**: id, risk\_id, playbook\_id, action\_type, tier, params (json), simulated\_outcome (json: resolves\_breach, new\_slack\_days), rank, rationale (text), status, idempotency\_key (unique), created\_at.

**approval**: id, recommendation\_id, approver\_user\_id, decision (APPROVED or REJECTED), comment, ts.

**readiness\_snapshot**: id, employee\_id, ts, score (int 0-100), band, breakdown (json), drivers (json list of what changed).

**audit\_log** (append-only): id, ts, actor, action, entity\_type, entity\_id, before (json), after (json), reason (text).

**notification**: id, ts, employee\_id, to\_role\_or\_user, channel (EMAIL or CHAT), subject, body, related\_task\_id, status.

**sim\_clock**: singleton row with `current_time`, `mode` (SIM or REAL).

**document**: id, employee\_id, task\_id, kind, filename, masked\_fields (json), extracted\_fields (json), verification\_status.

## 6. Configuration schemas (single source of truth)

Configs are loaded and validated by Pydantic at startup. Invalid config must fail startup with a clear message. The dependency graph is checked for cycles and unknown IDs.

### 6.1 Profile config (`config/profiles/*.yaml`)

```yaml
profile: india_full_time
display_name: India Full-Time
defaults:
  payroll_cutoff_day: 20
  business_calendar: holidays_in
variants:
  experienced:
    add_tasks: [HR-06, PAY-05]
  remote:
    remove_tasks: [IT-04]
    override:
      IT-01: { duration_days: 7 }
tasks:
  PAY-02:
    title: Bank proof verification
    owner_role: PAYROLL
    depends_on: [PAY-01]
    duration_days: 2
    deadline: { relative_to: join_date, offset_days: -5 }
    external_sla_days: null
    flags: { critical: false, mandatory: true, compliance: false }
    outcome_tags: [PAYROLL_SETUP_DELAYED]
  PAY-06:
    title: Payroll master data complete
    owner_role: PAYROLL
    depends_on: [PAY-02, PAY-04]
    duration_days: 1
    deadline: { relative_to: payroll_cutoff, offset_days: 0 }
    flags: { critical: true, mandatory: true, compliance: true }
    outcome_tags: [FIRST_SALARY_AT_RISK]
```

Supported `relative_to` values: `join_date`, `payroll_cutoff`. Offsets are in business days. Conditional tasks use `variants`; the plan generator applies `add_tasks`, `remove_tasks` (marked SKIPPED) and `override`.

### 6.2 Playbooks (`config/playbooks.yaml`)

```yaml
playbooks:
  - id: PB-REMIND
    action_type: SEND_REMINDER
    tier: AUTO
    applies_when: { owner_role: [NEW_HIRE], task_states: [REJECTED, IN_PROGRESS, READY] }
    effect: { reduce_remaining_days: 1 }
  - id: PB-OFFCYCLE
    action_type: OFFCYCLE_PAYROLL
    tier: MANAGER_APPROVAL
    applies_when: { outcome_tags: [FIRST_SALARY_AT_RISK] }
    effect: { extend_due_days: 5, target_task: PAY-06 }
```

Full playbook list is in Section 7.7. `effect` types: `reduce_remaining_days`, `extend_due_days`, `change_owner`, `halve_external_sla`, `shift_join_date_days`.

### 6.3 Scoring (`config/scoring.yaml`)

```yaml
weights: { critical: 0.40, slack: 0.25, compliance: 0.20, timeliness: 0.15 }
bands: { ready_min: 85, watch_min: 60 }
```

### 6.4 Policies (`config/policies.yaml`)

```yaml
slack_buffer_days: 1
rework_days: 2
owner_overdue_penalty_days: 0.5
owner_overdue_penalty_cap_days: 2
max_recommendations_per_risk: 3
```

## 7. Backend services: behaviour specification

### 7.1 Clock and business calendar (`core/clock.py`)

- Interface `Clock.now() -> datetime` (UTC, tz-aware). Implementations: `RealClock`, `SimClock` (reads and writes the `sim_clock` row).
- `advance(days=0, hours=0)` and `set_to(datetime)` are allowed only in SIM mode. Each call emits a `CLOCK_ADVANCED` event and triggers `monitor.evaluate_all()`.
- Business-day utilities: `add_business_days(date, n)`, `business_days_between(a, b)`. Weekends (Sat, Sun) and holidays from `config/holidays_in.yaml` are non-working days. Negative offsets must work.
- All services receive the clock by dependency injection. Tests use a fixed `SimClock`.

### 7.2 Plan generator (`services/plan_generator.py`)

Input: employee (profile\_key, is\_experienced, is\_remote, work\_state, join\_date). Steps:

1. Load the profile config; apply variants (`add_tasks`, `remove_tasks`, `override`). Removed tasks become `SKIPPED` instances so the UI can show Not applicable.
2. Compute `payroll_cutoff_date`: the next date on or after `join_date` whose day-of-month equals `payroll_cutoff_day`, moved to the previous business day if it falls on a non-working day.
3. Compute each `due_date` from its `relative_to` anchor and `offset_days` (business days).
4. Create `task_instance` and `task_dependency` rows. Reject cycles (`networkx.is_directed_acyclic_graph`) and unknown dependency IDs with a clear error.
5. Set initial states: tasks with no unfinished dependencies become `READY`, others `NOT_STARTED`.
6. Emit `PLAN_GENERATED` and write an audit entry. The operation is idempotent per employee (re-running does not duplicate tasks).

Optional enrichment (LLM, non-critical): welcome message and personalized checklist text, via `LLMService.draft_message`.

### 7.3 State machine (`services/state_machine.py`)

| From | To | Triggered by | Rules |
| --- | --- | --- | --- |
| NOT\_STARTED | READY | system | All dependencies are DONE or SKIPPED |
| READY | IN\_PROGRESS | owner | Only the owner role or assignee |
| IN\_PROGRESS | DONE | owner or system | Sets completed\_at; may unlock dependents |
| IN\_PROGRESS | REJECTED | verifier | Requires a reason; increments rework\_count; stores reason in meta |
| REJECTED | IN\_PROGRESS | submitter | Resubmission |
| READY or IN\_PROGRESS | BLOCKED | system or HR | Requires a reason |
| BLOCKED | READY or IN\_PROGRESS | system or HR | Returns to previous state |
| DONE | IN\_PROGRESS | HR or ADMIN | Reopen; requires a reason; audited |

Any other transition raises a `409 InvalidTransition` error. Each successful transition: writes `event_log`, writes `audit_log` (before and after), unlocks dependents that become READY, then calls `monitor.evaluate(employee_id)`.

### 7.4 Monitor loop (`services/monitor.py`)

`evaluate(employee_id)` runs after every task event and every clock change. It must be **deterministic and idempotent**:

1. Recompute derived readiness (NOT\_STARTED to READY).
2. Compute `earliest_finish` and `slack` for each open task (Section 7.5).
3. Upsert `risk` rows (key: task\_id plus status OPEN). Mark a risk RESOLVED when it no longer applies.
4. For each new or worsened MEDIUM or HIGH risk: run root cause (7.6), impact (7.6), then recommendations (7.7).
5. Auto-execute recommendations whose tier is AUTO (7.8).
6. Save a `readiness_snapshot` (7.9) and compute drivers (what changed since the previous snapshot).
7. Publish SSE events for everything that changed.

For the MVP run `evaluate` synchronously inside the request. Provide a function boundary so it can be moved to a queue later.

### 7.5 Risk engine (`services/risk.py`)

For each open task `t` (state not DONE or SKIPPED):

```
earliest_start(t)  = max(now, max(earliest_finish(d) for d in deps(t)))
remaining(t)       = duration(t) (if IN_PROGRESS, minus elapsed, minimum 0.5)
                     + rework_days if state == REJECTED
                     + owner_penalty(t)           # 0.5 day per overdue task of the same owner, capped at 2
                     + external_sla_days(t) if set and not yet started
earliest_finish(t) = add_business_days(earliest_start(t), remaining(t))
earliest_finish(d) for DONE deps = completed_at
slack(t)           = business_days_between(earliest_finish(t), due_date(t))   # negative means late
```

Risk levels: `slack < 0` is HIGH; `0 <= slack < slack_buffer_days` is MEDIUM; otherwise no risk. A task already past its due date is HIGH with reason OVERDUE.

Reason codes: UPSTREAM\_DELAY (an ancestor is late), REJECTED\_ANCESTOR (the chain contains a REJECTED task), OWNER\_OVERLOAD (penalty applied), EXTERNAL\_SLA (SLA dominates), CRITICAL\_GATE (the task has `is_critical` or leads to one). Output includes `predicted_breach_date` (= earliest\_finish when slack < 0) and `slack_days`.

### 7.6 Root cause and impact (`services/root_cause.py`, `services/impact.py`)

**Root cause:** among the at-risk task and all its ancestors, find the tasks that are not DONE or SKIPPED and whose own dependencies are all DONE or SKIPPED (the frontier). Choose the frontier task on the chain that determines the at-risk task's `earliest_finish` (the longest chain). Prefer REJECTED or BLOCKED tasks on ties. Return the root cause task plus the ordered chain from root cause to the at-risk task.

**Downstream impact:** traverse descendants of the root cause. For each, return `{task_id, title, due_date, projected_finish, breaches (bool), outcome_tags}`. A summary lists the distinct outcome tags (for example FIRST\_SALARY\_AT\_RISK, INSURANCE\_DEDUCTION\_DELAYED, DAY1\_ACCESS\_AT\_RISK) and whether any impacted task is critical.

### 7.7 Playbooks and recommender (`services/playbooks.py`, `services/recommender.py`)

| Playbook | Action | Tier | Applies when | Effect |
| --- | --- | --- | --- | --- |
| PB-REMIND | SEND\_REMINDER | AUTO | Root cause owned by NEW\_HIRE and state REJECTED, READY or IN\_PROGRESS | Reduces remaining days by 1 (expected faster response) |
| PB-FOLLOWUP | CREATE\_FOLLOWUP | AUTO | Root cause is a verification task (PAYROLL or HR) | Creates a follow-up task due in 1 business day |
| PB-REASSIGN | REASSIGN | MANAGER\_APPROVAL | Owner role has OWNER\_OVERLOAD | Changes assignee; removes owner penalty |
| PB-EXPEDITE | EXPEDITE\_EXTERNAL | MANAGER\_APPROVAL | Root cause has external\_sla\_days (for example BGV) | Halves the external SLA |
| PB-EXPRESS | EXPRESS\_SHIPPING | MANAGER\_APPROVAL | Root cause is IT-01 | Reduces duration by 2 days |
| PB-OFFCYCLE | OFFCYCLE\_PAYROLL | MANAGER\_APPROVAL | Impact includes FIRST\_SALARY\_AT\_RISK | Extends PAY-06 due date by 5 business days |
| PB-SHIFT-JOIN | SHIFT\_JOIN\_DATE | MANAGER\_AND\_HR\_APPROVAL | Any HIGH risk that remains after other options | Shifts join\_date by N days and recomputes anchored due dates |

Algorithm:

1. Filter playbooks by `applies_when`.
2. **Simulate** each on an in-memory copy of the graph and recompute slack. Record `resolves_breach` and `new_slack_days`.
3. Rank: playbooks that resolve the breach first, then lower tier (AUTO before approval), then smaller disruption. Keep the top `max_recommendations_per_risk`.
4. Generate a `rationale` text: LLM if enabled (it may only reference the playbook and the computed numbers), otherwise a template.
5. Set `idempotency_key = sha256(risk_id + playbook_id + sorted params)`; skip creation if it already exists.

### 7.8 Executor and approvals (`services/executor.py`)

- AUTO recommendations execute immediately after creation. Others stay PROPOSED until approved.
- Approval rules: MANAGER\_APPROVAL requires the hire's manager or ADMIN; MANAGER\_AND\_HR\_APPROVAL requires both a manager and an HR approval record before execution. Rejecting marks it REJECTED and the monitor may propose alternatives.
- Execution applies the `effect` to the real data (reassign, change due dates, create follow-up task), calls the relevant mock integration (for example `Notifier.send`), writes `event_log` and `audit_log`, sets status EXECUTED (or FAILED with an error), then calls `monitor.evaluate`.
- **Idempotent:** executing twice must not duplicate effects (check the status and the idempotency key inside a transaction).
- Superseded: when a risk resolves, its PROPOSED recommendations become SUPERSEDED.

### 7.9 Readiness score (`services/readiness.py`)

```
Critical    = done_mandatory_pre_join / total_mandatory_pre_join        # tasks with is_mandatory and due_date <= join_date
Slack       = healthy_open_critical / total_open_critical               # healthy = slack >= buffer; 1 if none open
Compliance  = (done + on_track) / total compliance tasks                # on_track = open with slack >= buffer
Timeliness  = 1 - overdue_count / count(tasks with due_date <= now)     # 1 if none due yet
Score       = round(100 * (w_critical*Critical + w_slack*Slack + w_compliance*Compliance + w_timeliness*Timeliness))
Band        = READY (>= 85) | WATCH (>= 60) | AT_RISK (< 60)
```

Store the breakdown and a `drivers` list (for example: PAY-02 rejected lowered Critical and Slack, by amounts). The UI must show the formula parts, not only the number.

### 7.10 Integrations and LLM

**Integration ports (`integrations/ports.py`):** protocols for `HRIS`, `ITService`, `PayrollService`, `BenefitsService`, `BGVService`, `LearningService`, `Notifier`. Mock implementations live in `integrations/mock/`, store their data in the database, support configurable latency and **failure injection** (`fail_next(task_key, reason)` via the simulation API), and never call external networks. `Notifier` writes to the `notification` table (shown in the UI Outbox).

**LLMService (`llm/service.py`):**

- `extract_document_fields(doc_text) -> ExtractedFields`
- `explain_risk(context) -> str` (input is the computed root cause and impact, not raw records)
- `draft_message(kind, context) -> Message`
- `justify_recommendations(options, context) -> list[str]`
- `answer_hire_question(question, hire_context) -> str` (grounded only in that hire's task data)

Rules: provider chosen by `LLM_PROVIDER` (`mock` default). All outputs validated with Pydantic. Timeout 8 seconds, one retry, then **fallback to templates**. Cache by input hash. `redaction.py` masks PAN, Aadhaar, bank numbers and emails before any provider call. Prompts live in `llm/prompts/` as versioned files. A feature flag `LLM_ENABLED` disables all LLM use; the product must work identically in function.

### 7.11 Audit and PII

- Every state change, recommendation, approval, execution, PII reveal and simulation action writes an `audit_log` row (who, what, why, before, after). Audit and event tables are insert-only (no update or delete endpoints).
- Sensitive fields (PAN, Aadhaar, bank account) are stored only as masked values plus last four characters in demo data. The UI shows masked values; HR or PAYROLL may click Reveal, which is audited and re-masks after 30 seconds.

## 8. API specification (REST, JSON)

Base path `/api/v1`. All endpoints require the bearer token except `/auth/*`. Errors use a consistent shape `{ code: string, message: string, details?: object }` with proper HTTP status codes. FastAPI auto-generates OpenAPI; the frontend generates types from it with `make types`.

| Method and path | Purpose | Request | Response |
| --- | --- | --- | --- |
| GET /auth/personas | List demo personas | none | `Persona[]` |
| POST /auth/login | Issue token | `{ userId }` | `{ token, user }` |
| GET /hires | List hires (filtered by role) | query: status, search | `HireSummary[]` (id, name, joinDate, readinessScore, band, openRiskCount) |
| POST /hires | Create hire and generate plan | `{ fullName, email, jobTitle, department, joinDate, workState, isExperienced, isRemote, managerId, profileKey }` | `HireDetail` |
| GET /hires/{id} | Hire detail | none | `HireDetail` (with masked fields) |
| GET /hires/{id}/plan | Tasks and dependencies | none | `{ tasks: Task[], edges: {from, to}[] }` |
| GET /tasks/mine | Tasks for the current user (owner queue or new hire) | query: state | `Task[]` |
| POST /tasks/{id}/transition | Change state | `{ to: TaskState, reason?: string, payload?: object }` | `Task` |
| POST /tasks/{id}/documents | Upload synthetic document (multipart) | file, kind | `Document` (with extracted fields) |
| GET /hires/{id}/risks | Risks with root cause and impact | query: status | `Risk[]` (each includes `rootCause`, `chain`, `impact`, `recommendations`) |
| GET /recommendations | Pending approvals for current user | query: status | `Recommendation[]` |
| POST /recommendations/{id}/approve | Approve | `{ comment? }` | `Recommendation` |
| POST /recommendations/{id}/reject | Reject | `{ comment? }` | `Recommendation` |
| GET /hires/{id}/readiness | Latest score and breakdown | none | `ReadinessSnapshot` |
| GET /hires/{id}/readiness/history | Score over time | none | `ReadinessSnapshot[]` |
| GET /hires/{id}/events | Event timeline | pagination | `Event[]` |
| GET /audit | Audit log | query: hireId, actor, from, to | `AuditEntry[]` |
| GET /notifications | Outbox | query: hireId | `Notification[]` |
| POST /hires/{id}/assistant | Ask a what-is-next question | `{ question }` | `{ answer, sources: taskIds[] }` |
| POST /hires/{id}/pii/reveal | Reveal masked field (audited) | `{ field }` | `{ value, expiresInSeconds }` |
| GET /config/profiles | View loaded config (admin) | none | profile, playbooks, scoring |
| GET /sim/clock | Current simulated time | none | `{ now, mode }` |
| POST /sim/clock/advance | Advance time | `{ days?, hours? }` | `{ now }` |
| POST /sim/inject | Inject a failure | `{ hireId, taskKey, kind: REJECT or DELAY or FAIL_INTEGRATION, reason }` | `{ ok }` |
| POST /sim/reset | Reset and reseed | `{ scenario?: string }` | `{ ok }` |
| GET /stream?hireId= | Server-sent events | none | events below |

**SSE event types:** `task.updated`, `risk.opened`, `risk.resolved`, `recommendation.created`, `recommendation.executed`, `readiness.updated`, `clock.advanced`, `notification.created`. Each event carries `{ type, hireId, ts, data }`. The frontend invalidates the matching TanStack Query keys on receipt.

**Task payload shape:** `{ id, hireId, templateKey, title, ownerRole, assigneeUserId, state, dueDate, durationDays, isCritical, isOverdue, slackDays, reasonCodes, outcomeTags, rejectionReason }`.

## 9. Frontend specification

### 9.1 Principles

- Desktop-first, responsive down to tablet. Clean, calm, enterprise look: neutral surfaces, one accent colour, clear status colours.
- **Status colours (design tokens):** READY and NOT\_STARTED grey, IN\_PROGRESS blue, DONE green, REJECTED red, BLOCKED orange, SKIPPED light grey with strikethrough, at-risk amber outline, HIGH risk red outline.
- Every screen has loading skeletons, empty states, and error states with a retry action. No blank screens.
- Server state via TanStack Query; invalidate on SSE events. No business logic in components; call the API client and render.
- Accessibility: keyboard navigation, visible focus, colour is never the only signal (use icons and text labels), ARIA labels on graph controls.
- Show times in IST and always show the simulated time in the top bar when in SIM mode.

### 9.2 Routes and screens

| Route | Roles | Purpose |
| --- | --- | --- |
| `/login` | public | Persona picker (cards for each demo persona with role description) |
| `/hires` | MANAGER, HR, ADMIN | Table of hires: name, join date, readiness score badge, open risks, owner of next task. Search and filters. Button: New hire |
| `/hires/new` | MANAGER, HR, ADMIN | Form to create a hire (fields in Section 8). Submitting shows the generated plan summary |
| `/hires/:id` | MANAGER, HR, ADMIN (and owners with scoped view) | Command center with tabs below |
| `/me` | NEW\_HIRE | Personal checklist, next step, document upload, assistant box |
| `/queue` | PAYROLL, IT, BENEFITS, HR | My tasks grouped by hire and due date, with actions |
| `/approvals` | MANAGER, HR, ADMIN | Pending recommendations with approve or reject |
| `/admin` | ADMIN | Config viewer (profiles, playbooks, scoring), audit log, simulation panel |

### 9.3 Hire command center (`/hires/:id`) tabs

1. **Overview:** readiness gauge (0-100 with band colour) plus the four-part breakdown bars (Critical, Slack, Compliance, Timeliness) and a Why did it change list (drivers). Next to it: top open risks (max 3), next actions due, and a score trend sparkline (Recharts).
2. **Plan:** task table with columns: ID, title, owner, state, due, slack, flags. Filters by owner, state, at-risk. Clicking a row opens the task drawer (details, history, dependencies, actions).
3. **Graph:** React Flow with dagre left-to-right layout. Nodes show ID, short title, state colour and a due date chip. Edges show dependencies. When a risk is selected: highlight the **root-cause chain** (thick red path), mark the root cause node with a pulse, and show **downstream impact** nodes with a dashed outline and a badge of their outcome tag. Provide zoom, fit, and a legend. Clicking a node opens the task drawer.
4. **Risks:** one card per open risk. Card sections: Summary (task, level, predicted breach date, slack), **Root cause** (task and chain as a breadcrumb), **Impact** (list with outcome tags), **Recommended actions** (up to 3, each showing action, tier badge, simulated outcome such as Resolves breach, new slack, rationale text, and the button Execute for AUTO items already executed, or Approve and Reject for tiered items). An Explain this panel shows the evidence used (reason codes and numbers) and the LLM explanation if enabled.
5. **Timeline:** merged chronological view of events and audit entries with actor, action and reason. Filter by type.
6. **Outbox:** simulated notifications (to, subject, body, related task).

### 9.4 Other screens

- **Task drawer:** title, owner, state badge, due date, duration, dependencies (links), rejection reason if any, history. Actions depend on role and state: Start, Complete, Reject (reason required), Block, Reopen (HR only). Document upload for tasks that require it, showing extracted fields (masked) and verification status.
- **New hire view (`/me`):** greeting with join date countdown, a progress ring, Your next step card, grouped checklist (Before you join, Week 1, First 30 days), upload buttons, and an Ask about your onboarding box that calls the assistant endpoint and shows the answer with the tasks it relied on.
- **Approvals:** list of cards, each with hire, risk summary, action, tier, simulated outcome and Approve or Reject with an optional comment. Show who has already approved for two-approval tiers.
- **Admin:** read-only config viewer, audit table with filters, and the **Simulation dock**.

### 9.5 Simulation dock (visible to ADMIN, collapsible, always on top)

Shows the current simulated date and time. Controls: +1 day, +3 days, advance to a chosen date, **Inject failure** (select hire, task, kind, reason), **Reset scenario** (choose Scenario A, B or Happy path). Each action calls the sim endpoints and the UI updates via SSE.

### 9.6 Suggested component and file layout

```
src/
  api/        client.ts  generated/ (openapi types)  hooks/ (useHires, useTasks, useRisks ...)
  auth/       AuthProvider.tsx  RequireRole.tsx
  components/ StatusBadge  ScoreGauge  BreakdownBars  RiskCard  RecommendationCard
              TaskDrawer  Timeline  EmptyState  ErrorState  Skeletons
  features/   hires/ plan/ graph/ risks/ approvals/ queue/ me/ admin/ sim/
  routes/     router.tsx  layouts/
  lib/        format.ts (IST dates)  sse.ts  constants.ts
```

## 10. Seed data and demo scenarios

The seed script (`make seed`) must create data **through the normal services** (plan generator, state machine), so events and audit entries exist. All data is synthetic. Simulation start: **2026-10-26 09:00 IST**.

### 10.1 Personas (users)

- Manager: Rohan Iyer (team Engineering). HR: Meera Shah. Payroll: Karthik Rao. IT: Divya Menon. Benefits: Asha Verma. Admin: Demo Admin.
- New hires (also users): Priya Nair, Arjun Mehta, Sana Khan.

### 10.2 Employees

| Name | Variant | Work state | Join date | Purpose |
| --- | --- | --- | --- | --- |
| Priya Nair | experienced, remote | Karnataka | 2026-11-16 | **Scenario A** (bank proof rejected) |
| Arjun Mehta | fresher, office | Maharashtra | 2026-11-23 | Happy path (also tests cutoff rollover to the next month) |
| Sana Khan | experienced, office | Tamil Nadu | 2026-11-18 | **Scenario B** (BGV delay) |

The seed also plays the first steps for each hire so the demo does not start from zero (for example, new hires complete early documents on time). Scenario hires must reach the exact states described below.

### 10.3 Scenario A: bank proof rejected (main demo)

1. Priya has completed HR-02, HR-03, HR-04 and submitted PAY-01 (bank proof).
2. Admin injects `REJECT` on PAY-02 with reason Name on bank proof does not match PAN.
3. **Expected:** PAY-02 becomes REJECTED; PAY-01 resubmission is requested; a MEDIUM risk appears on PAY-06 immediately (or HIGH once the clock passes the configured threshold; tune seed durations so that it becomes **HIGH when the clock reaches D-2**).
4. **Expected root cause:** PAY-02. Chain: PAY-02 to PAY-04 to PAY-06.
5. **Expected impact:** PAY-04, PAY-06, BEN-02 with outcome tags PAYROLL\_SETUP\_DELAYED, FIRST\_SALARY\_AT\_RISK, INSURANCE\_DEDUCTION\_DELAYED; critical impact true.
6. **Expected recommendations:** PB-REMIND (AUTO, executed: pre-filled correction request appears in Outbox), PB-FOLLOWUP (AUTO, executed), PB-OFFCYCLE (MANAGER\_APPROVAL, proposed, resolves breach).
7. Rohan approves PB-OFFCYCLE; it executes; PAY-06 due date extends; the risk resolves or drops to LOW; the readiness score falls when the risk appears and recovers afterwards, with drivers explaining each change.
8. Priya resubmits and PAY-02 completes; the audit trail shows the whole chain.

### 10.4 Scenario B: BGV delay (shorter)

1. Inject `DELAY` of 5 business days on HR-05 for Sana.
2. **Expected:** HIGH risk on HR-05 (due D-1) with reason EXTERNAL\_SLA; root cause HR-05; impact includes IT-05 (sensitive system access) with outcome tag SENSITIVE\_ACCESS\_DELAYED.
3. **Expected recommendations:** PB-EXPEDITE (MANAGER\_APPROVAL, halves SLA); if it does not resolve the breach, PB-SHIFT-JOIN (MANAGER\_AND\_HR\_APPROVAL) is also offered. Demonstrate the two-approval flow.

### 10.5 Happy path

Arjun's plan runs to completion with no HIGH risks and readiness at READY band, proving the system stays quiet when things are fine.

## 11. Task catalog (reference for `india_full_time.yaml`)

Deadlines are business days relative to join date D0, except PAY-06 which is relative to the payroll cutoff. Flags: **C** critical, **M** mandatory before joining, **K** compliance. Treat all values as defaults that live in config and can be tuned.

| ID | Task | Owner | Depends on | Days | Due | Flags |
| --- | --- | --- | --- | --- | --- | --- |
| HR-01 | Offer accepted, hire record created | HR | none | 0 | D-14 | M |
| HR-02 | Appointment letter issued and e-signed | HR | HR-01 | 2 | D-10 | M |
| HR-03 | Submit personal details and document pack | NEW\_HIRE | HR-02 | 3 | D-8 | M |
| HR-04 | Document verification | HR | HR-03 | 2 | D-6 | C, M, K |
| HR-05 | Background verification (external SLA 7 days) | HR | HR-03 | 7 | D-1 | C, M, K |
| HR-06 | Previous employer documents (experienced only) | NEW\_HIRE | HR-03 | 5 | D+30 | K |
| PAY-01 | Submit bank details and proof | NEW\_HIRE | HR-03 | 1 | D-7 | M |
| PAY-02 | Bank proof verification | PAYROLL | PAY-01 | 2 | D-5 | M |
| PAY-03 | Provide UAN and EPF details | NEW\_HIRE | HR-04 | 1 | D-3 | M, K |
| PAY-04 | PF, ESI and professional tax setup | PAYROLL | PAY-02, PAY-03 | 2 | D0 | M, K |
| PAY-05 | Tax regime and previous income details (experienced only) | NEW\_HIRE | HR-04 | 1 | D+3 | K |
| PAY-06 | Payroll master data complete (cutoff gate) | PAYROLL | PAY-02, PAY-04 | 1 | Payroll cutoff | C, K |
| IT-01 | Laptop allocated and shipped or ready | IT | HR-02 | 4 | D-3 | C, M |
| IT-02 | Email and directory account | IT | HR-04 | 1 | D-2 | M |
| IT-03 | Access provisioning (VPN, apps, repos) | IT | IT-02, MGR-01 | 2 | D-1 | C, M |
| IT-04 | Building access and ID card (office only) | IT | HR-04 | 2 | D0 | M |
| IT-05 | Sensitive system access (after BGV clearance) | IT | IT-03, HR-05 | 1 | D+3 | K |
| BEN-01 | Health insurance enrolment opened | BENEFITS | HR-04 | 1 | D0 | none |
| BEN-02 | Dependants details and enrolment filed | BENEFITS | BEN-01, PAY-04 | 3 | D+7 | K |
| BEN-03 | Insurer confirmation and e-card | BENEFITS | BEN-02 | 5 | D+15 | none |
| LRN-01 | Policy acknowledgements and NDA | NEW\_HIRE | HR-02 | 1 | D0 | M, K |
| LRN-02 | Mandatory trainings (security, code of conduct, POSH) | NEW\_HIRE | IT-02 | 3 | D+14 | K |
| LRN-03 | Role-specific learning path assigned | MANAGER | MGR-02 | 1 | D+1 | none |
| MGR-01 | Buddy assigned | MANAGER | HR-02 | 1 | D-5 | M |
| MGR-02 | First-week plan and 30/60/90 goals | MANAGER | MGR-01 | 2 | D-2 | M |
| MGR-03 | Welcome meeting scheduled | MANAGER | MGR-02 | 0.5 | D0 | none |
| MGR-04 | 30-day check-in | MANAGER | MGR-03 | 0.5 | D+30 | none |

Outcome tags to configure: PAY-02 PAYROLL\_SETUP\_DELAYED; PAY-04 PAYROLL\_SETUP\_DELAYED; PAY-06 FIRST\_SALARY\_AT\_RISK; BEN-02 INSURANCE\_DEDUCTION\_DELAYED; IT-03 DAY1\_ACCESS\_AT\_RISK; IT-05 SENSITIVE\_ACCESS\_DELAYED; HR-05 BGV\_CLEARANCE\_PENDING; IT-01 DAY1\_EQUIPMENT\_AT\_RISK.

Variants: **experienced** adds HR-06 and PAY-05 (fresher marks them SKIPPED); **remote** removes IT-04 and sets IT-01 duration to 7 days; **office** keeps IT-04. Professional tax details in PAY-04 vary by `work_state` through a small lookup in config (state to applicable yes or no and a note). The values here are placeholders to be verified.

## 12. Build stages

Each stage is a pull request from branch `stage/NN-name`. Each bullet under Tasks is intended to be **one or two commits**. A stage is done only when its acceptance criteria pass. Tag the merge commit `v0.NN`.

### Stage 0: Repo and tooling

**Goal:** a running skeleton with CI. **Tasks:** create repo layout (Section 3); backend `pyproject.toml` with FastAPI hello endpoint; frontend Vite React TS app; Docker Compose; Makefile targets; ruff, mypy, pytest, eslint, prettier, vitest configs; GitHub Actions CI; README and AGENTS.md. **Accept:** `make dev` serves backend and frontend; `make test` and `make lint` pass in CI. **Commits (examples):** `chore: scaffold backend with fastapi`, `chore: scaffold frontend with vite and typescript`, `ci: add lint and test workflow`, `docs: add readme and agent rules`.

### Stage 1: Config and domain models

**Goal:** typed config loading and the database schema. **Tasks:** enums; SQLAlchemy models and Alembic migration for all tables (Section 5); Pydantic config schemas; loaders for profile, playbooks, scoring, policies, holidays; cycle and unknown-ID validation; write `india_full_time.yaml` from Section 11 and a small `us_full_time.yaml` stub. **Accept:** startup fails with clear errors on invalid config; unit tests cover valid, cyclic and unknown-dependency configs.

### Stage 2: Clock and business calendar

**Goal:** deterministic time. **Tasks:** `Clock` interface, `RealClock`, `SimClock` (database-backed); business-day add and difference with holidays and negative offsets; unit tests including weekends and holidays. **Accept:** all tests pass; a lint rule or test forbids `datetime.now` outside `clock.py`.

### Stage 3: Plan generator

**Goal:** profile to task graph. **Tasks:** variant application (add, remove, override); payroll cutoff computation; due dates; task and dependency rows; initial READY states; idempotency. **Accept:** snapshot tests for Priya (experienced, remote), Arjun (fresher, office; cutoff rolls to the next month) and Sana; adding the US stub profile works with no code change.

### Stage 4: State machine, events, audit

**Goal:** safe task transitions. **Tasks:** transition table (Section 7.3); dependency unlocking; event bus (in-process) and `event_log`; `audit_log` writer; `InvalidTransition` error; unit tests for every allowed and forbidden transition. **Accept:** completing a task unlocks dependents; invalid transitions return 409; every transition writes event and audit rows.

### Stage 5: Auth, RBAC and core API

**Goal:** the first usable API. **Tasks:** persona login and JWT; `require_roles` dependency and ownership filters; endpoints for auth, hires (create, list, detail), plan, tasks (mine, transition); consistent error model; OpenAPI export; `make types` generating TS types. **Accept:** API tests per role (allowed and forbidden); OpenAPI file committed. **Frontend work can start in parallel from here using the OpenAPI types and mock handlers.**

### Stage 6: Risk engine

**Goal:** predict delay. **Tasks:** earliest finish and slack computation (Section 7.5); owner penalty; rework days; external SLA; risk levels and reason codes; risk upsert and resolve logic; unit tests with hand-built graphs. **Accept:** hand-calculated cases match exactly; a healthy plan produces no risks.

### Stage 7: Root cause and impact

**Goal:** explain and scope the problem. **Tasks:** frontier-based root cause with chain; descendant impact with projected finish, breaches and outcome tags; unit tests for branching graphs and ties (prefer REJECTED or BLOCKED). **Accept:** Scenario A returns root cause PAY-02, chain PAY-02 to PAY-04 to PAY-06, and the expected impact tags.

### Stage 8: Playbooks, recommender, approvals, executor

**Goal:** safe recovery. **Tasks:** playbook config and applicability filter; in-memory simulation of effects; ranking; idempotency key; recommendation and approval endpoints; executor with effects and audit; two-approval flow; supersede logic. **Accept:** Scenario A and B produce the expected recommendations; AUTO items execute once only; a MANAGER\_AND\_HR item needs both approvals; double execution is a no-op.

### Stage 9: Readiness score

**Goal:** explainable score. **Tasks:** formula (Section 7.9); config weights and bands; snapshots with drivers; endpoints for latest and history; unit tests. **Accept:** score decreases when a critical risk appears and recovers after resolution; breakdown sums correctly.

### Stage 10: Monitor loop, mock integrations, SSE, simulation API, seed

**Goal:** the whole backend works end to end. **Tasks:** `monitor.evaluate`; mock integrations with failure injection; notifier and outbox; SSE stream; sim endpoints (clock, inject, reset); `seed.py` creating the three hires and scenario states; scenario tests for A, B and the happy path. **Accept:** scenario tests pass headlessly; `make seed` plus API calls reproduce Section 10 exactly. Tag `v0.1-backend`.

### Stage 11: Frontend foundation

**Goal:** app shell. **Tasks:** router and layouts; auth provider and persona login; API client with generated types and TanStack Query hooks; SSE hook; design tokens; status components (badge, gauge, bars); skeleton, empty and error components; top bar with simulated time. **Accept:** each persona can log in and sees only the permitted navigation.

### Stage 12: Hires list, creation and Overview

**Tasks:** hires table with score badge; create-hire form with validation; Overview tab (gauge, breakdown, drivers, top risks, sparkline). **Accept:** creating a hire generates a plan and navigates to its Overview; score updates live on SSE events.

### Stage 13: Plan, task drawer, queue and new hire view

**Tasks:** plan table with filters; task drawer with role-aware actions and reject-with-reason; owner queue; new hire page with checklist, progress ring, document upload and assistant box (stub answer until Stage 16). **Accept:** an owner can start, complete and reject tasks; changes appear without refresh.

### Stage 14: Graph, risks and approvals

**Tasks:** React Flow graph with dagre layout, state colours, legend; root-cause chain and impact highlighting when a risk is selected; risk cards with recommendations; approvals page. **Accept:** Scenario A is fully demonstrable in the UI, including approve and watching the score recover.

### Stage 15: Simulation dock, admin, timeline, outbox

**Tasks:** dock with clock controls, failure injection and reset; admin config viewer and audit table; timeline and outbox tabs; PII reveal flow with re-mask. **Accept:** the admin can run Scenarios A and B end to end from the UI alone.

### Stage 16: LLM layer

**Tasks:** `LLMService` interface, `MockLLM`, provider adapter; redaction; structured output validation; caching; timeouts and fallbacks; wire document extraction, risk explanation, message drafting, recommendation rationale and the hire assistant. **Accept:** with `LLM_ENABLED=false` everything still works; with the mock provider outputs are deterministic; redaction tests prove no raw PAN, Aadhaar or bank numbers leave the system.

### Stage 17: Hardening, evaluation and docs

**Tasks:** evaluation suite of 15-20 scenarios with a results table (risk detection, root cause, impact, recommendation validity, plan correctness); error handling and edge cases; accessibility pass; Playwright test for Scenario A; architecture doc, ADRs, README with screenshots. **Accept:** evaluation table committed in `docs/evaluation.md`; e2e test passes in CI.

### Stage 18: Demo preparation

**Tasks:** demo script and timing; backup recording; one-command reset; presenter notes with the likely panel questions; final README polish. **Accept:** two timed run-throughs without intervention.

### Suggested parallel ownership (4 people)

- **A, platform and orchestration:** Stages 0, 1, 2, 3, 4, 5, 10.
- **B, intelligence:** Stages 6, 7, 8, 9 (starts from unit tests on hand-built graphs, so it needs only Stages 1 and 2).
- **C, frontend:** Stages 11-15 (starts after Stage 5 using mock handlers).
- **D, LLM, data, quality and demo:** config content, seed data, Stages 16, 17, 18 and the evaluation set.

## 13. Git workflow

- `main` is protected and always runnable. Work on `stage/NN-name` or `feat/<area>-<thing>` branches and merge by pull request with at least one teammate review.
- **Conventional Commits**, small and frequent: for example `feat(risk): compute earliest finish with rework days`, `test(risk): add slack cases for rejected ancestors`, `docs(prd): clarify cutoff rule`.
- Each pull request description includes: what and why, how to test, and the acceptance checklist of the stage.
- Commit under your **own identity**. When pairing, add a `Co-authored-by:` trailer. When an AI agent wrote most of a change, review it, run the tests, and say so honestly in the pull request. Do not rewrite history or fabricate commit timing to inflate activity; real, steady, reviewed commits are the strongest evidence of contribution.
- Add `CODEOWNERS` or a simple ownership table so each layer has a named owner who can explain it to the panel.
- Tag stable points (`v0.1-backend`, `v0.2-ui`, `v1.0-demo`).

## 14. Testing strategy

| Level | Tooling | What |
| --- | --- | --- |
| Unit | pytest | Clock, plan generator, state machine, risk, root cause, impact, playbooks, readiness (hand-calculated expected values) |
| Scenario | pytest | Scenarios A, B and happy path executed through the services with a fixed SimClock |
| API | pytest with FastAPI test client | Role access, error shapes, idempotency |
| Frontend | Vitest and React Testing Library | Key components and role-based rendering |
| End to end | Playwright | Scenario A through the UI |
| Evaluation | script | 15-20 scenarios producing a metrics table in `docs/evaluation.md` |

Coverage target: at least 80 percent on `services/`. Tests must be deterministic: no real clock, no network, mock LLM by default.

## 15. Non-functional requirements and security

- **Performance:** evaluation of one hire completes under 300 ms for 30 tasks; UI interactions respond within 200 ms; initial page load under 3 seconds on a laptop.
- **Reliability:** the app runs offline except for an optional LLM; no crash on malformed input; all errors are surfaced with clear messages.
- **Security and privacy:** synthetic data only; masked PII by default; audited reveal; RBAC enforced on the server; secrets only in environment variables; no PII in logs; redaction before LLM calls; mention India's DPDP Act principles (purpose limitation, data minimisation) in the architecture doc.
- **Observability:** structured logs with request IDs and employee IDs (not PII); an events timeline in the UI doubles as an operations view.
- **Maintainability:** modules under about 300 lines, services free of web concerns, config-driven behaviour, ADRs for decisions.

## 16. Definition of done and known risks

**Definition of done (whole MVP):** Scenarios A and B run in the UI from the simulation dock; the happy path stays quiet; config-only extension is demonstrated; LLM-off mode works; CI is green; evaluation table is committed; README lets a stranger run the app in under five minutes.

**Risks and mitigations**

| Risk | Mitigation |
| --- | --- |
| Scope creep | Build by stage; use the cut-line: drop the US stub, SSE (use polling), the assistant, then Scenario B polish, in that order. Never cut rules config, root cause and impact, approvals, audit log, or the explainable score |
| LLM slow or wrong during the demo | Mock or cached outputs, `LLM_ENABLED` switch, deterministic core |
| AI agent produces code nobody understands | Review every pull request; each owner explains their layer; keep modules small; write ADRs |
| Demo data drift | `make seed` and the reset endpoint; seeded fixtures in tests |
| Misstated India rules | Mark values as placeholders, keep all in config, verify with a reliable source before presenting |

## Appendix A: Stage kickoff prompt for the coding agent

Paste this when starting each stage, replacing the stage number:

```
Read AGENTS.md and docs/PRD.md. We are building Stage <N>: <name>.
Implement only this stage, following the referenced PRD sections exactly.
Work in small steps. After each step, run the tests and linters.
Propose a Conventional Commit message for each logical change.
If the PRD is ambiguous, pick the simplest option, write an ADR, and tell me.
When done, list: files changed, tests added, acceptance criteria status, and open questions.
Do not start the next stage.
```

## Appendix B: Glossary

- **Slack:** business days between a task's projected finish and its due date; negative means late.
- **Root cause:** the earliest unfinished task on the chain that determines a late task's projected finish.
- **Frontier task:** an unfinished task whose dependencies are all finished.
- **Playbook:** a predefined recovery action with an approval tier and a simulated effect.
- **Readiness score:** a 0-100 weighted measure of how prepared a new hire is for day one.
- **Cutoff gate:** the payroll deadline that decides whether the first salary is processed on time.
