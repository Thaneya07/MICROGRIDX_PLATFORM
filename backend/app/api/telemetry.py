"""
Telemetry API.

- GET /api/telemetry/microgrids/{microgrid_id}/current
- GET /api/telemetry/microgrids/{microgrid_id}/history
- GET /api/telemetry/devices/{device_id}/current
- GET /api/telemetry/devices/{device_id}/history
- POST /api/telemetry/hardware
- GET /api/telemetry/microgrids/{microgrid_id}/snapshot
- WebSocket /api/telemetry/microgrids/{microgrid_id}/stream

All responses are tagged with an explicit source (SIMULATED or HARDWARE)
per reading — never presented as ambiguous. Authentication/authorization is
not yet implemented (deferred to a later step); these endpoints are
unauthenticated in this phase.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.database.connection import SessionLocal, get_db
from app.schemas.telemetry import (
    HardwareTelemetryIn,
    DeviceReadingRead,
    DeviceReadingHistoryResponse,
    EnergyReadingHistoryResponse,
    EnergyReadingRead,
)
from app.schemas.telemetry_snapshot import MicrogridSnapshot
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.dependencies import get_telemetry_provider
from app.services.telemetry.service import TelemetryService
from app.services.telemetry.snapshot import build_microgrid_snapshot


_stream_logger = get_logger("app.api.telemetry.stream")

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
settings = get_settings()


class InvalidRangeError(AppError):
    status_code = 400
    error_code = "INVALID_RANGE"


def _validate_range(
    start: datetime,
    end: datetime,
    interval_minutes: int,
) -> None:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if end <= start:
        raise InvalidRangeError("`end` must be after `start`.")

    if end - start > timedelta(
        days=settings.TELEMETRY_HISTORY_MAX_SPAN_DAYS
    ):
        raise InvalidRangeError(
            f"Requested range exceeds the maximum of "
            f"{settings.TELEMETRY_HISTORY_MAX_SPAN_DAYS} days."
        )

    if interval_minutes < settings.TELEMETRY_HISTORY_MIN_INTERVAL_MINUTES:
        raise InvalidRangeError(
            f"`interval_minutes` must be >= "
            f"{settings.TELEMETRY_HISTORY_MIN_INTERVAL_MINUTES}."
        )


def get_telemetry_service(
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(get_telemetry_provider),
) -> TelemetryService:
    return TelemetryService(db, provider)


# ============================================================================
# PHYSICAL ESP32 HARDWARE INGESTION
# ============================================================================

@router.post("/hardware")
def receive_hardware_telemetry(
    payload: HardwareTelemetryIn,
    db: Session = Depends(get_db),
) -> dict:
    """
    Receive telemetry from the physical ESP32 device and persist it
    as HARDWARE telemetry.
    """

    from app.models.device import Device, DeviceStatus
    from app.models.telemetry import DeviceReading, TelemetrySource

    # Physical ESP32 device registered in the MicroGridX Demo Site.
    ESP32_DEVICE_ID = uuid.UUID(
        "a837768f-e454-4f6e-8c05-b6764c944d13"
    )

    device = db.get(Device, ESP32_DEVICE_ID)

    if device is None:
        raise AppError(
            "ESP32 hardware device is not registered."
        )

    recorded_at = (
        payload.recorded_at
        or datetime.now(timezone.utc)
    )

    # DeviceReading requires numeric power/voltage/current values.
    # Until INA219 is connected to the actual power circuit,
    # do not invent solar/battery measurements.
    voltage_v = (
        payload.solar_voltage_v
        if payload.solar_voltage_v is not None
        else (
            payload.battery_voltage_v
            if payload.battery_voltage_v is not None
            else 0.0
        )
    )

    current_a = (
        payload.solar_current_a
        if payload.solar_current_a is not None
        else (
            payload.battery_current_a
            if payload.battery_current_a is not None
            else 0.0
        )
    )

    power_w = (
        payload.solar_power_w
        if payload.solar_power_w is not None
        else (
            payload.battery_power_w
            if payload.battery_power_w is not None
            else 0.0
        )
    )

    reading = DeviceReading(
        device_id=device.id,
        recorded_at=recorded_at,
        power_w=max(0.0, power_w),
        voltage_v=max(0.0, voltage_v),
        current_a=max(0.0, current_a),
        temperature_c=payload.temperature_c,
        humidity_percent=payload.humidity_percent,
        status=DeviceStatus.ONLINE,
        source=TelemetrySource.HARDWARE,
    )

    db.add(reading)

    device.status = DeviceStatus.ONLINE
    device.last_seen_at = recorded_at

    db.commit()
    db.refresh(reading)

    return {
        "status": "stored",
        "source": "HARDWARE",
        "device_id": str(device.id),
        "microgrid_id": str(device.microgrid_id),
        "temperature_c": payload.temperature_c,
        "humidity_percent": payload.humidity_percent,
        "voltage_v": voltage_v,
        "current_a": current_a,
        "power_w": power_w,
        "relay_state": payload.relay_state,
        "recorded_at": recorded_at,
    }


# ============================================================================
# ENERGY TELEMETRY
# ============================================================================

@router.get(
    "/microgrids/{microgrid_id}/history",
    response_model=EnergyReadingHistoryResponse,
)
def get_microgrid_energy_history(
    microgrid_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval_minutes: int = Query(
        default=15,
        ge=1,
        le=1440,
    ),
    service: TelemetryService = Depends(get_telemetry_service),
) -> EnergyReadingHistoryResponse:

    _validate_range(
        start,
        end,
        interval_minutes,
    )

    readings = service.get_historical_energy_readings(
        microgrid_id,
        start,
        end,
        interval_minutes,
    )

    return EnergyReadingHistoryResponse(
        microgrid_id=microgrid_id,
        start=start,
        end=end,
        interval_minutes=interval_minutes,
        readings=[
            EnergyReadingRead.model_validate(reading)
            for reading in readings
        ],
    )


# ============================================================================
# DEVICE TELEMETRY
# ============================================================================

@router.get(
    "/devices/{device_id}/current",
    response_model=DeviceReadingRead,
)
def get_current_device_reading(
    device_id: uuid.UUID,
    service: TelemetryService = Depends(get_telemetry_service),
) -> DeviceReadingRead:

    reading = service.get_current_device_reading(
        device_id
    )

    return DeviceReadingRead.model_validate(reading)


@router.get(
    "/devices/{device_id}/history",
    response_model=DeviceReadingHistoryResponse,
)
def get_device_reading_history(
    device_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval_minutes: int = Query(
        default=15,
        ge=1,
        le=1440,
    ),
    service: TelemetryService = Depends(get_telemetry_service),
) -> DeviceReadingHistoryResponse:

    _validate_range(
        start,
        end,
        interval_minutes,
    )

    readings = service.get_historical_device_readings(
        device_id,
        start,
        end,
        interval_minutes,
    )

    return DeviceReadingHistoryResponse(
        device_id=device_id,
        start=start,
        end=end,
        interval_minutes=interval_minutes,
        readings=[
            DeviceReadingRead.model_validate(reading)
            for reading in readings
        ],
    )


# ============================================================================
# MICROGRID SNAPSHOT
# ============================================================================

@router.get(
    "/microgrids/{microgrid_id}/snapshot",
    response_model=MicrogridSnapshot,
)
def get_microgrid_snapshot(
    microgrid_id: uuid.UUID,
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(
        get_telemetry_provider
    ),
) -> MicrogridSnapshot:
    """
    One-call snapshot of a microgrid's current energy reading,
    every device's current reading, and its loads.

    This is the REST fallback for the WebSocket stream.
    """

    return build_microgrid_snapshot(
        db,
        provider,
        microgrid_id,
    )


# ============================================================================
# LIVE TELEMETRY WEBSOCKET STREAM
# ============================================================================

@router.websocket(
    "/microgrids/{microgrid_id}/stream"
)
async def stream_microgrid_telemetry(
    websocket: WebSocket,
    microgrid_id: uuid.UUID,
    interval_seconds: float = Query(
        default=settings.TELEMETRY_STREAM_INTERVAL_SECONDS,
        ge=1.0,
        le=60.0,
    ),
) -> None:
    """
    Live telemetry stream for the 3D visualization.

    Pushes a MicrogridSnapshot every `interval_seconds`.

    Each SQLAlchemy session is scoped to a single tick and
    closed after that tick.
    """

    await websocket.accept()

    # Validate that the microgrid exists.
    validation_db = SessionLocal()

    try:
        from app.models.microgrid import Microgrid

        microgrid = validation_db.get(
            Microgrid,
            microgrid_id,
        )

    finally:
        validation_db.close()

    if microgrid is None:
        await websocket.send_json(
            {
                "type": "error",
                "code": "NOT_FOUND",
                "message": (
                    f"Microgrid {microgrid_id} not found."
                ),
            }
        )

        await websocket.close(code=4404)
        return

    try:
        while True:

            tick_db = SessionLocal()

            try:
                # IMPORTANT:
                # The provider needs the current DB session when
                # hardware telemetry is being used.
                provider = get_telemetry_provider(
                    db=tick_db
                )

                snapshot = build_microgrid_snapshot(
                    tick_db,
                    provider,
                    microgrid_id,
                )

                payload = {
                    "type": "snapshot",
                    **snapshot.model_dump(
                        mode="json"
                    ),
                }

            except Exception as exc:
                _stream_logger.error(
                    "Telemetry stream tick failed",
                    exc_info=exc,
                    extra={
                        "context": {
                            "microgrid_id": str(
                                microgrid_id
                            )
                        }
                    },
                )

                payload = {
                    "type": "error",
                    "code": "STREAM_ERROR",
                    "message": str(exc),
                }

            finally:
                tick_db.close()

            await websocket.send_json(payload)

            await asyncio.sleep(
                interval_seconds
            )

    except WebSocketDisconnect:
        _stream_logger.info(
            "Telemetry stream client disconnected",
            extra={
                "context": {
                    "microgrid_id": str(
                        microgrid_id
                    )
                }
            },
        )