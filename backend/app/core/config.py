"""
Application configuration.

All configuration is sourced from environment variables (optionally loaded
from a local .env file during development). No secrets or environment
specific values are hardcoded here, and no permissive defaults are assumed
for production-sensitive settings such as CORS origins.
"""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General ---
    APP_NAME: str = "microgridx-api"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # --- Database ---
    DATABASE_URL: str = Field(
        default=...,
        description="SQLAlchemy-compatible PostgreSQL connection URL.",
    )
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_ECHO: bool = Field(default=False)

    # --- Telemetry ---
    # Which TelemetryProvider implementation to use. "simulation" is the
    # only implemented option today; "hardware" is reserved for future real
    # sensor ingestion (e.g. ESP32) behind the same interface.
    TELEMETRY_PROVIDER: str = Field(default="simulation")

    # Deterministic seed for the simulation provider. Changing this changes
    # the simulated "weather"/load pattern for every microgrid and device,
    # but keeps results reproducible for a given seed.
    SIMULATION_SEED: str = Field(default="microgridx-dev-seed")

    # Simulation magnitude parameters (watts), tunable without code changes.
    SIMULATED_PEAK_SOLAR_W: float = Field(default=4000.0)
    SIMULATED_BASE_LOAD_W: float = Field(default=350.0)
    SIMULATED_MORNING_PEAK_W: float = Field(default=900.0)
    SIMULATED_EVENING_PEAK_W: float = Field(default=1500.0)
    SIMULATED_BATTERY_CAPACITY_W: float = Field(default=3000.0)

    # Bounds for historical telemetry queries, to prevent unbounded
    # generation/query work from a single request.
    TELEMETRY_HISTORY_MAX_SPAN_DAYS: int = Field(default=30)
    TELEMETRY_HISTORY_MIN_INTERVAL_MINUTES: int = Field(default=1)

    @field_validator("TELEMETRY_PROVIDER")
    @classmethod
    def _validate_telemetry_provider(cls, value: str) -> str:
        allowed = {"simulation", "hardware"}
        if value not in allowed:
            raise ValueError(f"TELEMETRY_PROVIDER must be one of {sorted(allowed)}")
        return value

    # --- Analytics ---
    ANALYTICS_MIN_READINGS: int = Field(default=2)
    ANALYTICS_MAX_SPAN_DAYS: int = Field(default=90)
    ANALYTICS_DEFAULT_LOOKBACK_DAYS: int = Field(default=7)

    # --- Forecasting ---
    # Minimum number of readings required before a model may be trained at
    # all. Below this, training is refused outright (INSUFFICIENT_DATA)
    # rather than fitting an unreliable model.
    FORECAST_MIN_TRAINING_READINGS: int = Field(default=60)
    # Chronological split fractions for train/validation/test. Must sum to
    # < 1.0 (remainder goes to test).
    FORECAST_TRAIN_SPLIT: float = Field(default=0.7)
    FORECAST_VALIDATION_SPLIT: float = Field(default=0.15)
    FORECAST_RANDOM_STATE: int = Field(default=42)
    FORECAST_MAX_HORIZON_DAYS: int = Field(default=14)
    FORECAST_MAX_TRAINING_LOOKBACK_DAYS: int = Field(default=180)
    # Directory where trained model artifacts (joblib files) are persisted.
    # Deliberately outside the repository/working tree so trained binaries
    # are never accidentally committed.
    FORECAST_MODEL_DIR: str = Field(default="/tmp/microgridx_forecast_models")

    @field_validator("FORECAST_TRAIN_SPLIT", "FORECAST_VALIDATION_SPLIT")
    @classmethod
    def _validate_split_fraction(cls, value: float) -> float:
        if not (0.0 < value < 1.0):
            raise ValueError("Split fractions must be between 0 and 1.")
        return value

    # --- Live streaming (Step 6: 3D visualization) ---
    # Interval between broadcast ticks on the telemetry WebSocket stream.
    # Decoupled from any particular provider's data-generation cadence.
    TELEMETRY_STREAM_INTERVAL_SECONDS: float = Field(default=3.0)

    # --- Decision Engine / Optimization (Step 7) ---
    # Battery parameters. The device/telemetry model does not currently
    # report these from hardware, so they are explicit configured defaults
    # (documented here, not fabricated hardware specs) until a real
    # battery management system exposes them.
    DECISION_BATTERY_CAPACITY_WH: float = Field(default=5000.0)
    DECISION_BATTERY_MIN_SOC_PERCENT: float = Field(default=20.0)
    DECISION_BATTERY_MAX_SOC_PERCENT: float = Field(default=95.0)
    DECISION_BATTERY_MAX_CHARGE_W: float = Field(default=2000.0)
    DECISION_BATTERY_MAX_DISCHARGE_W: float = Field(default=2000.0)
    # Round-trip losses, applied asymmetrically to charge/discharge energy.
    # These also serve an optimization-structural purpose: they make
    # simultaneous nonzero charge and discharge strictly wasteful in the
    # LP's objective, so the solver naturally avoids it without needing
    # integer/binary "exclusivity" variables (see optimizer.py docstring).
    DECISION_BATTERY_CHARGE_EFFICIENCY: float = Field(default=0.95)
    DECISION_BATTERY_DISCHARGE_EFFICIENCY: float = Field(default=0.95)

    # Optimization horizon. Matches the interval_minutes granularity the
    # forecasting service already supports (see app/services/forecasting).
    DECISION_HORIZON_STEPS: int = Field(default=8)
    DECISION_INTERVAL_MINUTES: int = Field(default=30)

    # Objective weights — all configurable, all documented in
    # app/services/decision/objective.py. No monetary/tariff term exists:
    # this project has no tariff data source, so economic optimization is
    # explicitly unavailable rather than fabricated.
    DECISION_WEIGHT_GRID_IMPORT: float = Field(default=1.0)
    DECISION_WEIGHT_GRID_EXPORT: float = Field(default=0.1)
    DECISION_WEIGHT_PEAK: float = Field(default=0.5)
    DECISION_WEIGHT_DEGRADATION: float = Field(default=0.05)

    DECISION_MIN_TELEMETRY_READINGS: int = Field(default=1)

    # Operating mode classification (fulfills the Phase 1 OperatingMode
    # contract in app/services/decision_engine.py). Rule-based, layered on
    # top of the optimizer's output — see app/services/decision/mode.py
    # for the full documented logic.
    DECISION_EMERGENCY_SOC_BUFFER_PERCENT: float = Field(default=5.0)

    # --- CORS ---
    # Comma-separated list of allowed origins. No wildcard default is used
    # so that a misconfigured deployment fails closed rather than open.
    CORS_ORIGINS: str = Field(default="http://localhost:5173")

    @field_validator("ENVIRONMENT")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        allowed = {"development", "test", "staging", "production"}
        if value not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {sorted(allowed)}")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> "Settings":
    """Return a cached Settings instance (single source of truth per process)."""
    return Settings()
