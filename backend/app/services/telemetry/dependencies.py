"""
Provider factory / FastAPI dependency.

Resolves the configured `TelemetryProvider` implementation so routes and
services depend only on the abstract interface, never on a concrete
provider class.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.connection import get_db
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.hardware import HardwareTelemetryProvider
from app.services.telemetry.simulation import SimulationTelemetryProvider


def get_telemetry_provider(
    db: Session = Depends(get_db),
) -> TelemetryProvider:
    settings = get_settings()

    if settings.TELEMETRY_PROVIDER == "hardware":
        return HardwareTelemetryProvider(db)

    return SimulationTelemetryProvider()