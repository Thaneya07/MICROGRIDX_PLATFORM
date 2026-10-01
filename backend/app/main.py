"""
MicroGridX API application entrypoint.

Phase 1 foundation: health checks, CORS, structured logging, centralized
error handling, and clean application startup/shutdown. No business
functionality (AI, decisions, telemetry) is implemented here.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import decision, demo, energy, forecast, health, microgrid, telemetry
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.api.battery_health import router as battery_health_router
from app.api import ai_forecasts
from app.api import fault_detection
from app.api import ai_decision
settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting MicroGridX API",
        extra={"context": {"environment": settings.ENVIRONMENT}},
    )
    yield
    logger.info("Shutting down MicroGridX API")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MicroGridX API",
        description="Smart Energy Monitoring and Management Platform - Phase 1 Foundation",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(telemetry.router)
    app.include_router(energy.router)
    app.include_router(forecast.router)
    app.include_router(decision.router)
    app.include_router(microgrid.router)
    app.include_router(demo.router)
    app.include_router(battery_health_router)
    app.include_router(ai_forecasts.router)
    app.include_router(fault_detection.router)
    app.include_router(ai_decision.router)

    return app


app = create_app()
