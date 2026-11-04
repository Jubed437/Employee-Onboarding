# Agent rules

Follow the PRD in [docs/PRD.md](docs/PRD.md) as the source of truth.

- Build one PRD stage at a time.
- Use synthetic personal data only.
- Keep business logic in backend services, not API routers or React components.
- Use the `Clock` service for all business time.
- Keep the LLM optional and deterministic in tests.
- Use strict typing and run the documented checks before committing.
- Use Conventional Commits with small, focused changes.
