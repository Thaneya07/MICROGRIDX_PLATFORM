# MicroGridX

MicroGridX is an AI-driven Smart Energy Monitoring and Management Platform.
It analyzes customer energy usage, available generation/storage, environmental
conditions, and load information to eventually forecast demand, forecast
renewable generation, and automatically manage controllable loads across
`NORMAL_MODE`, `ECO_MODE`, and `EMERGENCY_MODE`.

**This repository currently implements Phase 1 only: the foundational
platform (frontend, backend, database, migrations, and clean interfaces for
future AI/Decision Engine work).** No AI models, predictions, or automated
energy-management decisions exist yet — see [Phase 1 scope](#phase-1-scope)
below.

## Architecture

```
Customer/Admin UI
        |
        v
React frontend (TypeScript, Vite)
        |
        | HTTP/REST
        v
FastAPI backend (Python, Pydantic, SQLAlchemy)
        |
        +--------------------+
        |                    |
        v                    v
   PostgreSQL           AI Services (Phase 2+, interface only today)
                             |
                             v
                    Decision Engine (Phase 2+, interface only today)
                             |
                             v
                Energy-management actions (Phase 2+)
```

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for a
fuller description, including the AI/Decision Engine data flow this
foundation is built to support.

## Technology stack

| Layer         | Technology                                   |
|---------------|-----------------------------------------------|
| Frontend      | React 18, TypeScript, Vite                    |
| Backend       | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x |
| Database      | PostgreSQL 16                                 |
| Migrations    | Alembic                                       |
| Backend tests | Pytest                                        |
| Frontend tests| Vitest, Testing Library                       |
| Infrastructure| Docker, Docker Compose                        |

## Repository structure

```
MICROGRIDX_PLATFORM/
├── frontend/                 React + TypeScript + Vite app
│   ├── src/
│   │   ├── app/               App root and pages
│   │   ├── components/ui/     Reusable UI primitives
│   │   ├── services/          API client, env config
│   │   ├── types/             Shared TypeScript types
│   │   ├── hooks/              React hooks
│   │   └── styles/             Design tokens (CSS variables)
│   └── Dockerfile
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── api/                Route modules (health, ...)
│   │   ├── core/                Config, logging, error handling
│   │   ├── database/            Engine/session, declarative base
│   │   ├── models/               SQLAlchemy ORM models
│   │   ├── schemas/              Pydantic schemas
│   │   └── services/             AI + Decision Engine interfaces
│   ├── alembic/                 Migrations
│   ├── tests/                   Pytest suite
│   └── Dockerfile
├── docs/architecture/         Architecture documentation
├── .env.example
├── docker-compose.yml
└── README.md
```

## Environment setup

Copy the example environment file and adjust values as needed:

```bash
cp .env.example .env
```

The backend also reads `backend/.env` directly when run outside Docker
(pydantic-settings loads it automatically); an equivalent example is not
duplicated there — use the root `.env.example` as the source of truth for
which variables exist.

## Docker setup (primary path)

```bash
docker compose up --build
```

This starts three services:

- `postgres` — PostgreSQL 16, with a named volume (`postgres_data`) so data
  persists across restarts.
- `backend` — FastAPI, listening on `BACKEND_PORT` (default `8000`). Waits
  for Postgres to report healthy before running Alembic migrations and
  starting Uvicorn.
- `frontend` — the Vite production build served as static files on
  `FRONTEND_PORT` (default `5173`).

No secrets are baked into the images; all configuration comes from
environment variables (see `.env.example`).

## Local development (without Docker)

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env   # then edit DATABASE_URL to point at your local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

By default the frontend expects the backend at `http://localhost:8000`
(`VITE_API_BASE_URL`).

## Database migrations

Migrations are managed with Alembic from within `backend/`:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

The current migration (`create foundational tables`) creates `users`,
`customers`, `microgrids`, `devices`, and `loads`.

## Testing

**Backend**

```bash
cd backend
pytest -v
```

**Frontend**

```bash
cd frontend
npm run test     # Vitest
npm run build    # type-checks (tsc -b) and produces a production build
```

## Phase 2, Step 4 (energy analytics)

Built directly on persisted telemetry, with calculation logic kept out of
the API layer:

```
EnergyReading (DB) -> AnalyticsService -> metrics / patterns / profile -> API
```

- **Metrics** (`app/services/analytics/metrics.py`): energy totals (Wh) via
  trapezoidal integration of power over time, solar self-consumption, grid
  import/export energy, peak/average demand, load factor, renewable
  contribution %, grid dependency %, and battery charge/discharge/
  throughput where battery data exists.
- **Patterns** (`app/services/analytics/patterns.py`): hourly consumption/
  generation averages, weekday vs weekend averages, peak-period detection
  (statistically meaningful peaks only — a flat load correctly reports no
  peaks), base-load estimation (10th percentile), consumption variability
  (coefficient of variation), solar/load correlation (Pearson), grid
  import energy share, battery active fraction.
- **Customer energy profile** (`app/services/analytics/profile.py`):
  combines the above into a profile with data-driven behavioural
  characteristics (e.g. `evening-heavy`, `high-variability`,
  `grid-dependent`, `solar-dominant`) — each characteristic carries the
  exact numeric comparison that produced it, never an unexplained label.
- `GET /api/energy/microgrids/{id}/summary`
- `GET /api/energy/microgrids/{id}/patterns`
- `GET /api/energy/microgrids/{id}/profile`

All three require an explicit `source` (defaults to `SIMULATED`) so
simulated and (future) hardware readings are never blended into one
aggregate, and raise `422 INSUFFICIENT_DATA` rather than fabricating a
result when too few readings exist in the requested range.

### Telemetry consistency review (done as part of this step)

Before building analytics, the telemetry layer was audited for logical
consistency and two real defects were fixed:

1. Battery charge/discharge was invisible in the microgrid-level energy
   balance (SOC could move with no corresponding power flow accounted for).
   Added a signed `battery_power_w` field and rebuilt the simulation so
   `generation + battery_discharge + grid_import == consumption +
   battery_charge + grid_export` holds by construction, with a regression
   test checking this invariant across a full simulated day.
2. No database-level protection against physically-invalid values (e.g.
   negative power) or duplicate `(entity, timestamp, source)` rows — added
   `CHECK` and `UNIQUE` constraints to `energy_readings`/`device_readings`.

Not yet implemented: forecasting/AI, anomaly detection, the decision/
optimization engine, recommendations, authentication, and the customer/
admin dashboards.

## Phase 2A scope (telemetry foundation)

Added on top of the Phase 1 foundation, without modifying it:

- `EnergyReading` and `DeviceReading` tables — time-series telemetry kept
  separate from the core domain tables (`Microgrid`, `Device`, ...)
- A provider-based telemetry architecture (`TelemetryProvider` interface)
  so a future real-sensor provider (e.g. ESP32 hardware) can replace the
  simulator without changing any API or business logic
- `SimulationTelemetryProvider` — deterministic, seeded, time-of-day-aware
  simulation (solar generation curve, morning/evening consumption peaks,
  grid import/export, bounded battery state of charge). Every reading is
  tagged `source: "SIMULATED"` and is never presented as a hardware reading
- `GET /api/telemetry/microgrids/{id}/current` and `/history`
- `GET /api/telemetry/devices/{id}/current` and `/history`

Not yet implemented: forecasting/AI, anomaly detection, the decision/
optimization engine, recommendations, authentication, and the customer/
admin dashboards — these are later Phase 2 steps.

## Phase 1 scope

Implemented in this phase:

- Repository, frontend, and backend foundations
- PostgreSQL integration via SQLAlchemy, with Alembic migrations
- Foundational domain models: `User`, `Customer`, `Microgrid`, `Device`, `Load`
- `GET /api/health` and `GET /api/health/database` (the latter performs a
  real database round-trip)
- Structured JSON logging and centralized, consistently-shaped error handling
- CORS configuration, environment-based settings, clean DB session
  dependency injection
- Reusable frontend UI primitives (Button, Card, Badge, Input,
  StatusIndicator, MetricCard, PageHeader, LoadingState/EmptyState/ErrorState,
  Modal) and a working frontend↔backend connectivity page
- Abstract `AIService` and `DecisionEngine` interfaces — every method is an
  explicit `NotImplementedError` placeholder
- Docker Compose environment for all three services
- Automated backend (Pytest) and frontend (Vitest) test suites

## Explicitly deferred to Phase 2+

- Actual AI models (demand forecasting, solar forecasting, usage analysis,
  recommendation generation)
- Actual Decision Engine logic (mode selection, load-shifting actions)
- Telemetry ingestion and storage
- Authentication and authorization (login, sessions, RBAC enforcement)
- Customer and admin dashboards
- Alerts, recommendations, savings tracking, decision history
- Real-time updates (WebSocket) between backend and frontend

## Security notes

- Passwords are never stored in plaintext — the `users` table only ever
  holds a `password_hash` column, and no password-handling logic exists yet
  because authentication itself is deferred to a later phase.
- No secrets are committed to this repository; all sensitive configuration
  is environment-variable driven (see `.env.example`).
- `Settings.ENVIRONMENT` is validated against an explicit allow-list, and
  `CORS_ORIGINS` has no wildcard default, so a misconfigured deployment
  fails closed rather than open.
