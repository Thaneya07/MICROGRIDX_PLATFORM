"""
Provider factory / FastAPI dependency.

Resolves the configured `TelemetryProvider` implementation so routes and
services depend only on the abstract interface, never on a concrete
provider class.
"""
from functools import lru_cache

from app.core.config import get_settings
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.hardware import HardwareTelemetryProvider
from app.services.telemetry.simulation import SimulationTelemetryProvider


@lru_cache
def get_telemetry_provider() -> TelemetryProvider:
    settings = get_settings()
    if settings.TELEMETRY_PROVIDER == "hardware":
        return HardwareTelemetryProvider()
    return SimulationTelemetryProvider()
