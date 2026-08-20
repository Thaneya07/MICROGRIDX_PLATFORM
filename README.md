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

## Phase 2, Step 7 (decision engine / optimization)

A decision-SUPPORT layer that turns telemetry + analytics + forecasts into
optimized battery/load recommendations, integrated into the Step 6 3D
visualization as a labeled `DecisionPanel`.

```
EnergyReading (current) + Forecast (Step 5)      Load (priority/status)
        |                                               |
        v                                               v
   OptimizationInputs  ------------------------------->  |
        |                                                |
        v                                                |
   Battery dispatch LP (scipy.optimize.linprog, HiGHS)    |
        |                                                |
        v                                                v
   Constraint verification  ---->  Rule-based load recommendations
        |
        v
   Decision (persisted) ----> DecisionPanel (3D visualization sidebar)
```

**CRITICAL SAFETY BOUNDARY: MicroGridX currently provides decision
support and optimization recommendations; it does not automatically
actuate physical hardware.** No code path in this repository sends a
command to any device. `POST /api/decision/{id}/approve` only records a
human approval/rejection status in the database — it never triggers
hardware action.

- **Algorithm**: a small Linear Program (`scipy.optimize.linprog`,
  HiGHS backend — already a transitive dependency via scikit-learn, no
  new package added), solving battery charge/discharge/grid-import/
  grid-export for each step of a configurable horizon (default 8 steps ×
  30 min). Chosen over MILP (round-trip efficiency losses in the
  objective make simultaneous charge+discharge strictly wasteful, so the
  LP relaxation naturally avoids it without integer variables), QP (no
  quadratic terms exist in the objective), and MPC-as-a-framework (this
  *is* a receding-horizon re-solve already — see
  `app/services/decision/optimizer.py` docstring for the full rationale).
- **Objective**: minimize grid import + a small grid-export penalty + a
  linearized peak-shaving term + a battery-throughput (degradation) proxy.
  **No monetary/tariff term** — this project has no tariff data source,
  so economic optimization is explicitly reported as
  `"unavailable: no tariff data configured"` in every decision's
  provenance rather than fabricated.
- **Battery constraints**: capacity, min/max SOC, max charge/discharge
  power, and round-trip efficiencies are explicit configuration defaults
  (`DECISION_BATTERY_*` settings) — documented as such, since the current
  device/telemetry model does not report real battery specs from
  hardware.
- **Load recommendations**: rule-based (DEFER lowest-priority controllable
  loads under grid-import pressure, RUN_NOW controllable-off loads when
  there's forecasted solar surplus), layered on top of the LP result — the
  Load model has no continuous power variable suitable for the LP itself.
- **Fallback**: if no trained forecast model exists (or SOC is unknown, or
  the LP is infeasible), the optimizer is never invoked — a
  `SAFE_FALLBACK` decision is persisted with an explicit reason, never a
  silently-returned "optimal" result.
- `POST /api/decision/microgrids/{id}/optimize`,
  `GET /api/decision/microgrids/{id}/latest`,
  `GET /api/decision/microgrids/{id}/history`,
  `POST /api/decision/{decision_id}/approve`.
- `decisions` table: the optimization *output* (recommendation, expected
  outcomes, constraint checks, explanation, provenance), not duplicated
  telemetry.

Not yet implemented: authentication, and (deliberately, per this step's
scope) any actual hardware control.

## Phase 2, Step 6 (3D energy system visualization)

An interactive 3D representation of a microgrid's physical energy system
(solar array, battery, meter/grid connection, load controller, sensors,
loads, and animated energy-flow paths), built with React Three Fiber +
Three.js + Drei inside the existing frontend. Observation-only — it does
not control any device.

```
EnergyReading / DeviceReading (DB)
        |
        v
TelemetryService (existing, unmodified)
        |
        v
build_microgrid_snapshot() (new, composes existing service calls)
        |
        +-----------------------------+
        |                             |
        v                             v
GET /api/telemetry/microgrids/    WS /api/telemetry/microgrids/
  {id}/snapshot (REST fallback)     {id}/stream (live, ticks every
                                     TELEMETRY_STREAM_INTERVAL_SECONDS)
        |                             |
        +-----------------------------+
        |
        v
useTelemetryStream() — tries WS first, falls back to REST polling
        |
        v
MicrogridScene (React Three Fiber) — solar/battery/meter/load-controller/
sensor meshes + animated flow lines, all driven by the snapshot
```

- **New endpoints** (both additive, appended to `app/api/telemetry.py`
  without touching any existing route): `GET .../snapshot` (REST) and
  `WS .../stream` (live). Both return the identical `MicrogridSnapshot`
  shape (`app/schemas/telemetry_snapshot.py`) — energy reading, every
  device reading tagged with `device_type`, and the microgrid's loads.
- **Hardware readiness**: the snapshot is built from the existing,
  provider-agnostic `TelemetryProvider` interface. When
  `HardwareTelemetryProvider` (ESP32 + INA219 + DHT22, still a stub) is
  implemented, neither endpoint nor the 3D scene requires any change —
  the stream simply starts broadcasting `source: "HARDWARE"` snapshots.
- **Source separation**: `source` is present on every snapshot and every
  device reading; the frontend's `DataSourceBadge` always shows SIMULATED
  or HARDWARE, never blending or guessing.
- **Forecast integration**: `ForecastPanel` renders forecast data in a
  clearly separate, badge-labeled panel — never merged into the live 3D
  scene or live metrics, per the product rule that forecast and live
  measurements must always be visually and structurally distinct.
- **Resilience**: `useTelemetryStream` tries the WebSocket first (4s
  connect timeout) and falls back to polling the REST snapshot endpoint if
  the socket cannot be established or drops. Loading, disconnected, empty
  (no energy reading yet), and error states are all handled explicitly in
  `VisualizationPage`.

Not yet implemented: authentication, the decision/optimization engine, and
direct hardware control (out of scope for this step, as instructed).

## Phase 2, Step 5 (forecasting)

Forecasting for `DEMAND` (consumption) and `SOLAR_GENERATION`, built on
persisted telemetry, with training as an explicit, auditable action:

```
EnergyReading (DB, single source)
    -> chronological train/validation/test split
    -> calendar feature preparation
    -> RandomForestRegressor training
    -> evaluation (MAE/RMSE/SMAPE/R2) vs. a seasonal-naive baseline
    -> persistence (model file + ForecastModel metadata row)
```

- **Algorithm selection** (`app/services/forecasting/model.py`, full
  rationale in the module docstring): RandomForestRegressor, chosen over
  deep sequence models (LSTM/TFT/PatchTST — too data-hungry for current
  telemetry volumes) and over boosted trees (a bagged ensemble is more
  robust to a small dataset with default hyperparameters, and its
  per-tree prediction spread gives an honest, if approximate, uncertainty
  estimate). This is a documented trade-off, not a fixed requirement —
  revisit once more training history exists.
- **Features** (`features.py`): calendar-only (cyclically-encoded
  hour-of-day, day-of-week, month, weekend flag). No lag features — the
  only data source today (`SimulationTelemetryProvider`) generates values
  as a deterministic function of time-of-day, so lag features would add
  recursive-forecast complexity without evidence of benefit; revisit once
  hardware telemetry with real short-term autocorrelation exists.
- **Baseline** (`baseline.py`): seasonal-naive (historical average per
  hour-of-day × weekend/weekday bucket) — the honest floor every trained
  model is compared against on the same held-out test set. In one live
  verification run, the baseline actually beat the trained model on the
  `DEMAND` target (MAE 36.9 vs 57.1) while the trained model won clearly
  on `SOLAR_GENERATION` (MAE 84.3 vs 143.5) — both results are reported
  as-is, not adjusted to favor the "advanced" model.
- **Uncertainty**: derived from the spread across the Random Forest's
  individual trees (mean ± ~1.96·std), explicitly labeled in every API
  response as an approximation, not a calibrated confidence interval.
- `POST /api/forecast/microgrids/{id}/train?target=DEMAND|SOLAR_GENERATION`
  — refuses to train (`422 INSUFFICIENT_DATA`) below
  `FORECAST_MIN_TRAINING_READINGS` (default 60) readings for the requested
  source.
- `GET /api/forecast/microgrids/{id}?target=&start=&end=&interval_minutes=`
  — `404` if no model has been trained yet for that target/source (training
  is never triggered implicitly); `400 INVALID_HORIZON` beyond
  `FORECAST_MAX_HORIZON_DAYS` (default 14).
- `GET /api/forecast/microgrids/{id}/models` — full training history/audit
  trail for a microgrid.

Every response carries an explicit data-provenance note: models are
trained and evaluated on `SIMULATED` telemetry only, and all metrics are
DEMO/SIMULATION results, not validated real-world accuracy. `source` is
required end-to-end (train, predict) so SIMULATED and HARDWARE data are
never blended into one model.

Not yet implemented: anomaly detection, the decision/optimization engine,
recommendations, authentication, and the customer/admin dashboards.

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
