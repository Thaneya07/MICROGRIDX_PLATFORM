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

# --- Step 6 additions (3D visualization): snapshot + live stream ---
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from app.database.connection import SessionLocal
from app.schemas.telemetry_snapshot import MicrogridSnapshot
from app.services.telemetry.snapshot import build_microgrid_snapshot
from app.core.logging import get_logger

_stream_logger = get_logger("app.api.telemetry.stream")

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


# ============================================================================
# Step 6 additions: microgrid snapshot (REST) + live telemetry stream (WS)
#
# These are new, additive endpoints for the 3D visualization feature. They
# do not modify any endpoint or function above. Both use the same
# MicrogridSnapshot DTO (app/schemas/telemetry_snapshot.py), built from the
# existing, unmodified TelemetryService — so the WebSocket stream and its
# REST fallback are guaranteed to return identical payload shapes.
# ============================================================================


@router.get("/microgrids/{microgrid_id}/snapshot", response_model=MicrogridSnapshot)
def get_microgrid_snapshot(
    microgrid_id: uuid.UUID,
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(get_telemetry_provider),
) -> MicrogridSnapshot:
    """
    One-call snapshot of a microgrid's current energy reading, every
    device's current reading (tagged with device_type), and its loads.
    This is the REST fallback for the WebSocket stream below: the 3D
    visualization frontend polls this endpoint if the WebSocket connection
    cannot be established, using the exact same payload shape either way.
    """
    return build_microgrid_snapshot(db, provider, microgrid_id)


@router.websocket("/microgrids/{microgrid_id}/stream")
async def stream_microgrid_telemetry(
    websocket: WebSocket,
    microgrid_id: uuid.UUID,
    interval_seconds: float = Query(default=settings.TELEMETRY_STREAM_INTERVAL_SECONDS, ge=1.0, le=60.0),
) -> None:
    """
    Live telemetry stream for the 3D visualization (Step 6).

    Pushes a MicrogridSnapshot every `interval_seconds`. Uses the
    configured TelemetryProvider (get_telemetry_provider) exactly like the
    REST endpoints — when a real HardwareTelemetryProvider is implemented
    for ESP32/INA219/DHT22 sensors, this endpoint requires no changes: it
    will simply start broadcasting HARDWARE-sourced snapshots instead of
    SIMULATED ones, using the same MicrogridSnapshot shape.

    Each SQLAlchemy session is scoped to a single tick (opened and closed
    within the loop) rather than held open for the lifetime of the
    connection, since a visualization client may stay connected far longer
    than a normal request/response cycle.
    """
    await websocket.accept()

    # Validate the microgrid exists before starting the broadcast loop.
    validation_db = SessionLocal()
    try:
        from app.models.microgrid import Microgrid

        microgrid = validation_db.get(Microgrid, microgrid_id)
    finally:
        validation_db.close()

    if microgrid is None:
        await websocket.send_json(
            {"type": "error", "code": "NOT_FOUND", "message": f"Microgrid {microgrid_id} not found."}
        )
        await websocket.close(code=4404)
        return

    provider = get_telemetry_provider()

    try:
        while True:
            tick_db = SessionLocal()
            try:
                snapshot = build_microgrid_snapshot(tick_db, provider, microgrid_id)
                payload = {"type": "snapshot", **snapshot.model_dump(mode="json")}
            except Exception as exc:  # noqa: BLE001 - reported to the client, connection stays open
                _stream_logger.error(
                    "Telemetry stream tick failed",
                    exc_info=exc,
                    extra={"context": {"microgrid_id": str(microgrid_id)}},
                )
                payload = {"type": "error", "code": "STREAM_ERROR", "message": str(exc)}
            finally:
                tick_db.close()

            await websocket.send_json(payload)
            await asyncio.sleep(interval_seconds)
    except WebSocketDisconnect:
        _stream_logger.info(
            "Telemetry stream client disconnected",
            extra={"context": {"microgrid_id": str(microgrid_id)}},
        )
