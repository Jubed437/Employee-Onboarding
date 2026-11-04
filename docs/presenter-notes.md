# Presenter notes

## Likely panel questions

### Why SQLite?

SQLite keeps the MVP offline and reproducible. SQLAlchemy models and relational
constraints remain PostgreSQL-compatible, so deployment storage can change
without changing workflow behavior.

### Where does the LLM make decisions?

Nowhere in the workflow-critical path. Scores, dates, compliance, approvals,
risk levels, and state transitions are deterministic. The optional LLM only
explains, drafts, extracts, or answers from the hire's task context.

### What happens when the LLM is unavailable?

`LLM_ENABLED=false` is the default. Provider calls are redacted, validated,
cached, retried once, and then replaced with deterministic templates.

### How is a root cause selected?

The service selects the highest-priority blocked or rejected frontier task,
then traces dependencies and calculates downstream impact. A rejected task
wins a projected-finish tie.

### How do you demonstrate repeatability?

The simulated clock, seeded personas, three synthetic hires, failure injection,
and `make demo-reset` restore the same starting point for every run.

### What would be production work?

Replace mock integrations, use managed PostgreSQL, add external identity and
document verification, store secrets in a secret manager, and add operational
observability and deployment controls.
