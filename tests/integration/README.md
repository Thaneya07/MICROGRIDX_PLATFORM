# Integration tests

This directory is reserved for cross-service integration tests (frontend +
backend + database running together, e.g. against a `docker compose up`
stack).

Phase 1 verification is covered by:

- `backend/tests/` — Pytest suite exercising the FastAPI app against a real
  PostgreSQL database (health checks, model metadata, service contracts).
- `frontend/src/**/__tests__/` — Vitest suite exercising UI primitives and
  the API client.
- Manual verification of end-to-end frontend → backend → database
  connectivity via the `ConnectivityPage`, documented in the project README
  and the Phase 1 implementation report.

Full black-box integration tests (e.g. spinning up `docker compose` and
driving the built frontend with a browser automation tool) are deferred to
a later phase once there is meaningful business functionality to exercise
end-to-end.
