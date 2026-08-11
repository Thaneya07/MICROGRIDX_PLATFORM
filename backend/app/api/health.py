"""
Health-check endpoints.

- GET /api/health              Basic liveness check (no dependencies).
- GET /api/health/database     Verifies real database connectivity.
"""
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger
from app.database.connection import check_database_connection
from app.schemas.health import DatabaseHealthResponse, HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Basic liveness probe. Does not touch the database."""
    return HealthResponse(status="ok", service=settings.APP_NAME)


@router.get("/database", response_model=DatabaseHealthResponse)
def health_database() -> DatabaseHealthResponse:
    """Readiness probe that verifies the database can actually be reached."""
    try:
        check_database_connection()
    except Exception as exc:  # noqa: BLE001 - intentionally broad, converted to AppError
        logger.error("Database health check failed", exc_info=exc)
        raise ServiceUnavailableError(
            message="Database connection failed.",
            details={"reason": str(exc)},
        ) from exc

    return DatabaseHealthResponse(status="ok", database="connected")
