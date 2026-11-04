# Stage 17 evaluation

The evaluation matrix covers the deterministic workflow boundaries and the
optional LLM boundary. Results were collected with the backend test suite and
the frontend production build.

| # | Scenario | Area | Expected result | Result |
|---:|---|---|---|---|
| 1 | Valid hire payload | Plan | Hire is accepted | PASS |
| 2 | Invalid email | Validation | Request is rejected | PASS |
| 3 | Missing auth token | API security | `401` response | PASS |
| 4 | Wrong role | RBAC | `403` response | PASS |
| 5 | Profile variant | Plan | Profile-specific tasks generated | PASS |
| 6 | Repeated plan generation | Idempotency | No duplicate plan | PASS |
| 7 | Dependency cycle | Config | Configuration validation fails | PASS |
| 8 | Upstream delay | Risk | Delay and critical-gate risk detected | PASS |
| 9 | Overdue owner | Risk | Owner-overload reason is emitted | PASS |
| 10 | Rejected frontier tie | Root cause | Rejected task wins the tie | PASS |
| 11 | Descendant traversal | Impact | All downstream tasks and tags included | PASS |
| 12 | AUTO playbook | Recommendation | Effect executes once | PASS |
| 13 | Approval playbook | Approval | Required approval is enforced | PASS |
| 14 | Readiness snapshot | Scoring | Breakdown and band are persisted | PASS |
| 15 | Simulation clock | Monitor | Time advances through the clock service | PASS |
| 16 | LLM disabled | LLM | Deterministic fallback is used | PASS |
| 17 | Sensitive document text | Redaction | Raw identifiers do not cross provider boundary | PASS |
| 18 | Provider timeout | Resilience | One retry then template fallback | PASS |

## Accessibility and UI hardening

- Primary navigation has an explicit accessible label.
- Score and progress visualizations expose text alternatives through
  `aria-label`.
- Error states use `role="alert"`.
- Form controls are associated with visible labels and required fields use
  native validation.
- The Scenario A Playwright test exercises login, hire creation, plan
  generation, and the readiness overview.
