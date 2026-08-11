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
