# Demo runbook

The demo is designed for a 10-minute live run and a 4-minute backup recording.
All data is synthetic and can be restored with one command.

## Before the session

1. Install backend and frontend dependencies.
2. Run `make demo-reset`.
3. Start the API with `make dev`.
4. Start Vite with `npm --prefix frontend run dev`.
5. Confirm `http://localhost:8000/health` returns `{"status":"ok"}`.
6. Keep the backup recording from the last successful run available locally.

## Timed live script

| Time | Action | Demonstrate |
|---:|---|---|
| 0:00 | Log in as Demo Admin | Synthetic persona login and role-aware navigation |
| 0:45 | Open Command center | Active hires and readiness portfolio |
| 1:45 | Open Priya Nair | Readiness score, band, formula breakdown, and drivers |
| 3:00 | Open Plan | Dependency-aware task graph and task states |
| 4:00 | Open Risks | Deterministic risk, root cause, downstream impact, and recommendations |
| 5:30 | Open Approvals | Manager/HR approval boundary |
| 6:30 | Open Simulation | Advance the clock by one day |
| 7:15 | Return to Overview | Readiness update through the monitor/SSE boundary |
| 8:00 | Open Audit and Outbox | Append-only audit trail and notification mock |
| 9:00 | Create a new hire | Configuration-driven plan generation and readiness overview |
| 10:00 | Answer questions | Use the presenter notes below |

If a live step fails, stop and use the backup recording rather than changing
the database manually. Re-run `make demo-reset` before a second live attempt.

## Backup recording

Record one successful run after `make demo-reset` and store it outside Git
(for example, `demo-recordings/stage-18.mp4`). The recording should show the
same timed sequence and must not contain real employee data, credentials, or
environment variables. Recreate it after any UI or seed-data change.
