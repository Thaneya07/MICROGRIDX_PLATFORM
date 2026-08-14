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
