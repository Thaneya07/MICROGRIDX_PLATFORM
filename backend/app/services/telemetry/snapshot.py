"""
Microgrid snapshot builder (Step 6: 3D visualization).

Deliberately built as a thin composition layer on top of the existing,
unmodified `TelemetryService` -- it does not duplicate or reimplement any
telemetry logic, it only assembles one microgrid-level view (energy
reading + every device reading + loads) for consumers that need the whole
picture in one call: the WebSocket stream and its REST fallback.
"""
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.customer import Customer
from app.models.device import Device
from app.models.load import Load
from app.models.microgrid import Microgrid
from app.models.telemetry import TelemetrySource
from app.schemas.telemetry import EnergyReadingRead
from app.schemas.telemetry_snapshot import DeviceSnapshotReading, LoadSnapshot, MicrogridSnapshot
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.service import TelemetryService

logger = get_logger(__name__)


def _provider_source_fallback(provider: TelemetryProvider) -> TelemetrySource:
    from app.services.telemetry.hardware import HardwareTelemetryProvider

    if isinstance(provider, HardwareTelemetryProvider):
        return TelemetrySource.HARDWARE
    return TelemetrySource.SIMULATED


def build_microgrid_snapshot(
    db: Session, provider: TelemetryProvider, microgrid_id: uuid.UUID
) -> MicrogridSnapshot:
    microgrid = db.get(Microgrid, microgrid_id)
    if microgrid is None:
        raise NotFoundError(f"Microgrid {microgrid_id} not found.")

    service = TelemetryService(db, provider)

    energy_reading_dto = None
    energy_reading_error = None
    try:
        energy_reading_row = service.get_current_energy_reading(microgrid_id)
        energy_reading_dto = EnergyReadingRead.model_validate(energy_reading_row)
        source = energy_reading_row.source
    except Exception as exc:  # noqa: BLE001 - reported to the client, not swallowed
        logger.error(
            "Failed to obtain current energy reading for snapshot",
            exc_info=exc,
            extra={"context": {"microgrid_id": str(microgrid_id)}},
        )
        energy_reading_error = str(exc)
        source = _provider_source_fallback(provider)

    devices = db.execute(select(Device).where(Device.microgrid_id == microgrid_id)).scalars().all()
    device_snapshots: List[DeviceSnapshotReading] = []
    for device in devices:
        try:
            reading = service.get_current_device_reading(device.id)
            device_snapshots.append(
                DeviceSnapshotReading(
                    device_id=device.id,
                    device_type=device.device_type,
                    status=reading.status,
                    recorded_at=reading.recorded_at,
                    power_w=reading.power_w,
                    voltage_v=reading.voltage_v,
                    current_a=reading.current_a,
                    source=reading.source,
                )
            )
        except Exception as exc:  # noqa: BLE001 - one device failing must not break the whole snapshot
            logger.error(
                "Failed to obtain current device reading for snapshot",
                exc_info=exc,
                extra={"context": {"device_id": str(device.id)}},
            )

    # Loads belong to a Customer, which belongs to a Microgrid -- there is
    # no direct microgrid_id on Load, so this joins through Customer.
    load_rows = db.execute(
        select(Load).join(Customer, Load.customer_id == Customer.id).where(Customer.microgrid_id == microgrid_id)
    ).scalars().all()
    load_snapshots = [
        LoadSnapshot(
            load_id=load.id,
            name=load.name,
            category=load.category,
            priority=load.priority,
            controllable=load.controllable,
            control_mode=load.control_mode,
            status=load.status,
        )
        for load in load_rows
    ]

    return MicrogridSnapshot(
        microgrid_id=microgrid.id,
        name=microgrid.name,
        location=microgrid.location,
        status=microgrid.status,
        server_time=datetime.now(timezone.utc),
        source=source,
        energy_reading=energy_reading_dto,
        devices=device_snapshots,
        loads=load_snapshots,
        energy_reading_error=energy_reading_error,
    )
