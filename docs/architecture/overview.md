# MicroGridX Architecture

## Overview

MicroGridX is split into three layers today, with two more layers defined
as contracts for future phases:

```
Customer/Admin UI
        |
        v
React frontend (TypeScript, Vite)
        |
        | HTTP/REST
        v
FastAPI backend (authoritative application layer)
        |
        +--------------------+
        |                    |
        v                    v
   PostgreSQL           AI Services  (interface only — Phase 1)
                             |
                             v
                    Decision Engine (interface only — Phase 1)
                             |
                             v
                Energy-management actions (Phase 2+)
```

## Frontend → Backend → Database (implemented)

- The **React frontend** contains no energy-management business logic. Its
  responsibility in Phase 1 is limited to reusable UI primitives and a
  connectivity page that proves it can reach the backend.
- The **FastAPI backend** is the single authoritative application layer.
  All domain rules, validation, and (eventually) energy-management
  decisions live here — never in the frontend.
- **PostgreSQL** is accessed exclusively through SQLAlchemy from the
  backend. The frontend never talks to the database directly.
- Requests flow: browser → Vite dev server / static bundle → `fetch()` to
  the FastAPI backend over HTTP → SQLAlchemy session → PostgreSQL.

### Request lifecycle

1. Frontend calls `apiClient.getHealth()` / `apiClient.getDatabaseHealth()`.
2. FastAPI receives the request, resolves the `get_db` dependency (which
   yields a scoped SQLAlchemy session and guarantees it is closed
   afterward), and executes the handler.
3. `/api/health/database` runs `SELECT 1` against PostgreSQL through the
   session to verify real connectivity — it does not assume the database is
   reachable.
4. Responses are serialized through Pydantic schemas. Errors of any kind
   (validation, not-found, unexpected exceptions) are normalized by the
   centralized exception handlers in `app/core/errors.py` into a single
   consistent JSON shape.

## Backend → AI Services → Decision Engine → Energy-management actions (future)

This is the path Phase 1 deliberately does **not** implement, but is built
to support cleanly:

- **AI Services** (`app/services/ai.py`) will eventually forecast demand,
  forecast solar/renewable generation, analyze usage patterns, and generate
  customer recommendations. In Phase 1 this is an abstract `AIService`
  class whose methods all raise `NotImplementedError` — there is no
  fabricated prediction data anywhere in the codebase.
- The **Decision Engine** (`app/services/decision_engine.py`) will
  eventually consume AI Service output plus real-time context (grid state,
  available generation, load priorities) to choose an operating mode
  (`NORMAL_MODE`, `ECO_MODE`, `EMERGENCY_MODE`) and plan load-management
  actions. In Phase 1 this is likewise an abstract `DecisionEngine` class
  with `NotImplementedError` placeholders.
- **Energy-management actions** (turning controllable loads on/off,
  shifting load timing) are the eventual output of the Decision Engine.
  Nothing in this repository performs such actions yet — the `Load` model
  captures `controllable` and `control_mode` as domain data only.

Building the interfaces now — rather than deferring them entirely — means
the backend's dependency injection, request/response contracts, and domain
models will not need to be reshaped when real AI and decision logic are
added in a later phase.

## Domain model

```
users (1) ────── (1) customers (N) ────── (1) microgrids
                       │                          │
                       │ (N)                      │ (N)
                       ▼                          ▼
                     loads                     devices
                                                   │
                                                   │ (0..N optional)
                                                   ▼
                                              customers
```

- A `User` has at most one `Customer` profile (one-to-one).
- A `Customer` belongs to exactly one `Microgrid`.
- A `Microgrid` has many `Device`s; a `Device` may optionally be attributed
  to a specific `Customer` (e.g. a smart meter at their premises) or may
  belong to the microgrid generally (e.g. shared solar inverter).
- A `Customer` has many `Load`s (controllable or non-controllable
  appliances/circuits).

Telemetry, prediction, recommendation, savings, alert, and decision-history
tables are intentionally not part of Phase 1's schema — they belong to the
phases that implement AI Services and the Decision Engine.

## Error handling contract

Every API error response — validation failures, not-found errors, database
unavailability, and unexpected exceptions — is normalized to:

```json
{
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Human readable message",
    "details": { }
  }
}
```

This is implemented once, centrally, in `app/core/errors.py`, rather than
per-endpoint, so new endpoints inherit consistent error behavior for free.

## Configuration and security posture

- All configuration is environment-variable driven (`app/core/config.py`);
  there are no hardcoded secrets or connection strings.
- `ENVIRONMENT` is validated against an explicit allow-list and
  `CORS_ORIGINS` has no permissive wildcard default, so misconfiguration
  fails closed.
- Passwords are represented only as `password_hash` in the `User` model —
  no plaintext password field exists, and no authentication logic (which
  would need to choose a hashing scheme) has been added yet, since
  authentication itself is out of scope for Phase 1.
