"""
Telemetry API.

- GET /api/telemetry/microgrids/{microgrid_id}/current
- GET /api/telemetry/microgrids/{microgrid_id}/history
- GET /api/telemetry/devices/{device_id}/current
- GET /api/telemetry/devices/{device_id}/history

All responses are tagged with an explicit `source` (SIMULATED or HARDWARE)
per reading — never presented as ambiguous. Authentication/authorization is
not yet implemented (deferred to a later step); these endpoints are
unauthenticated in this phase.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.connection import get_db
from app.schemas.telemetry import (
    DeviceReadingHistoryResponse,
    DeviceReadingRead,
    EnergyReadingHistoryResponse,
    EnergyReadingRead,
)
from app.services.telemetry.dependencies import get_telemetry_provider
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.service import TelemetryService

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
settings = get_settings()


class InvalidRangeError(AppError):
    status_code = 400
    error_code = "INVALID_RANGE"


def _validate_range(start: datetime, end: datetime, interval_minutes: int) -> None:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if end <= start:
        raise InvalidRangeError("`end` must be after `start`.")
    if end - start > timedelta(days=settings.TELEMETRY_HISTORY_MAX_SPAN_DAYS):
        raise InvalidRangeError(
            f"Requested range exceeds the maximum of {settings.TELEMETRY_HISTORY_MAX_SPAN_DAYS} days."
        )
    if interval_minutes < settings.TELEMETRY_HISTORY_MIN_INTERVAL_MINUTES:
        raise InvalidRangeError(
            f"`interval_minutes` must be >= {settings.TELEMETRY_HISTORY_MIN_INTERVAL_MINUTES}."
        )


def get_telemetry_service(
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(get_telemetry_provider),
) -> TelemetryService:
    return TelemetryService(db, provider)


@router.get("/microgrids/{microgrid_id}/current", response_model=EnergyReadingRead)
def get_current_microgrid_energy(
    microgrid_id: uuid.UUID,
    service: TelemetryService = Depends(get_telemetry_service),
) -> EnergyReadingRead:
    reading = service.get_current_energy_reading(microgrid_id)
    return EnergyReadingRead.model_validate(reading)


@router.get("/microgrids/{microgrid_id}/history", response_model=EnergyReadingHistoryResponse)
def get_microgrid_energy_history(
    microgrid_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval_minutes: int = Query(default=15, ge=1, le=1440),
    service: TelemetryService = Depends(get_telemetry_service),
) -> EnergyReadingHistoryResponse:
    _validate_range(start, end, interval_minutes)
    readings = service.get_historical_energy_readings(microgrid_id, start, end, interval_minutes)
    return EnergyReadingHistoryResponse(
        microgrid_id=microgrid_id,
        start=start,
        end=end,
        interval_minutes=interval_minutes,
        readings=[EnergyReadingRead.model_validate(r) for r in readings],
    )


@router.get("/devices/{device_id}/current", response_model=DeviceReadingRead)
def get_current_device_reading(
    device_id: uuid.UUID,
    service: TelemetryService = Depends(get_telemetry_service),
) -> DeviceReadingRead:
    reading = service.get_current_device_reading(device_id)
    return DeviceReadingRead.model_validate(reading)


@router.get("/devices/{device_id}/history", response_model=DeviceReadingHistoryResponse)
def get_device_reading_history(
    device_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval_minutes: int = Query(default=15, ge=1, le=1440),
    service: TelemetryService = Depends(get_telemetry_service),
) -> DeviceReadingHistoryResponse:
    _validate_range(start, end, interval_minutes)
    readings = service.get_historical_device_readings(device_id, start, end, interval_minutes)
    return DeviceReadingHistoryResponse(
        device_id=device_id,
        start=start,
        end=end,
        interval_minutes=interval_minutes,
        readings=[DeviceReadingRead.model_validate(r) for r in readings],
    )
