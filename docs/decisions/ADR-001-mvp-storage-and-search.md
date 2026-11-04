# ADR-001: MVP storage and search boundary

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The onboarding MVP needs reliable task dependencies, date calculations, state
transitions, approvals, audit history, and explainable readiness scores. It does
not require semantic document retrieval to complete those workflows.

The project should remain easy to run offline while preserving a path to a
production database and optional AI capabilities.

## Decision

1. Use SQLite for the MVP through SQLAlchemy and Alembic.
2. Keep the relational schema PostgreSQL-compatible.
3. Represent task dependencies in relational tables and use `networkx` for graph
   algorithms where appropriate.
4. Keep all core decisions deterministic and configuration-driven.
5. Implement an LLM service boundary with a deterministic mock, disabled by
   default.
6. Do not add embeddings or a vector database in the MVP.

Embeddings and vector search may be added later for policy retrieval, document
classification, or a semantic hire assistant. Such functionality must remain
behind an optional integration boundary and must not decide compliance, dates,
approvals, scores, or task state.

## Consequences

### Positive

- The demo runs offline with minimal operational setup.
- Core behaviour is testable with deterministic fixtures.
- Relational data remains easy to inspect, audit, and migrate.
- A future PostgreSQL deployment and optional retrieval layer remain possible.

### Negative

- SQLite is not intended for high-concurrency production workloads.
- Semantic search features will require a later design and provider decision.
- Some future assistant capabilities may initially use keyword or structured
  retrieval rather than embeddings.

## Reconsideration triggers

Revisit this decision when at least one of these is true:

- The product needs semantic search across a growing policy/document corpus.
- Retrieval quality is a measured bottleneck for an accepted user workflow.
- Concurrent production workloads exceed the practical limits of SQLite.
