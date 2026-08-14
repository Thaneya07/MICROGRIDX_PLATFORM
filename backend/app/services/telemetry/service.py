"""
Telemetry service.

Coordinates between the configured `TelemetryProvider` and the database:

- "current" reads always ask the provider for a live snapshot and persist
  it (write-through), so every current reading is durable and later
  queryable as history.
- "historical" reads are served from already-persisted rows where
  available; for a simulation provider, any requested-but-missing points
  in the range are deterministically (re)generated and persisted so the
  same range always returns the same values on repeated calls.

This keeps the API and downstream consumers (future analytics/decision
code) provider-agnostic: they only ever see `EnergyReading`/`DeviceReading`
rows tagged with an explicit `TelemetrySource`.
"""
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.device import Device
from app.models.microgrid import Microgrid
from app.models.telemetry import DeviceReading, EnergyReading
from app.services.telemetry.base import TelemetryProvider

logger = get_logger(__name__)


class TelemetryService:
    def __init__(self, db: Session, provider: TelemetryProvider):
        self.db = db
        self.provider = provider

    # --- microgrid-level energy readings ---

    def get_current_energy_reading(self, microgrid_id: uuid.UUID) -> EnergyReading:
        self._require_microgrid(microgrid_id)
        data = self.provider.get_current_energy_reading(microgrid_id)
        row = EnergyReading(
            microgrid_id=data.microgrid_id,
            recorded_at=data.recorded_at,
            consumption_w=data.consumption_w,
            generation_w=data.generation_w,
            grid_import_w=data.grid_import_w,
            grid_export_w=data.grid_export_w,
            available_energy_w=data.available_energy_w,
            battery_soc_percent=data.battery_soc_percent,
            battery_power_w=data.battery_power_w,
            source=data.source,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        logger.info(
            "Recorded current energy reading",
            extra={"context": {"microgrid_id": str(microgrid_id), "source": data.source.value}},
        )
        return row

    def get_historical_energy_readings(
        self, microgrid_id: uuid.UUID, start: datetime, end: datetime, interval_minutes: int
    ) -> List[EnergyReading]:
        self._require_microgrid(microgrid_id)

        existing = self.db.execute(
            select(EnergyReading)
            .where(EnergyReading.microgrid_id == microgrid_id)
            .where(EnergyReading.recorded_at >= start)
            .where(EnergyReading.recorded_at <= end)
            .order_by(EnergyReading.recorded_at)
        ).scalars().all()
        existing_timestamps = {row.recorded_at for row in existing}

        generated = self.provider.get_historical_energy_readings(microgrid_id, start, end, interval_minutes)
        missing = [d for d in generated if d.recorded_at not in existing_timestamps]

        new_rows = [
            EnergyReading(
                microgrid_id=d.microgrid_id,
                recorded_at=d.recorded_at,
                consumption_w=d.consumption_w,
                generation_w=d.generation_w,
                grid_import_w=d.grid_import_w,
                grid_export_w=d.grid_export_w,
                available_energy_w=d.available_energy_w,
                battery_soc_percent=d.battery_soc_percent,
                battery_power_w=d.battery_power_w,
                source=d.source,
            )
            for d in missing
        ]
        if new_rows:
            self.db.add_all(new_rows)
            self.db.commit()

        result = self.db.execute(
            select(EnergyReading)
            .where(EnergyReading.microgrid_id == microgrid_id)
            .where(EnergyReading.recorded_at >= start)
            .where(EnergyReading.recorded_at <= end)
            .order_by(EnergyReading.recorded_at)
        ).scalars().all()
        return list(result)

    # --- device-level readings ---

    def get_current_device_reading(self, device_id: uuid.UUID) -> DeviceReading:
        device = self._require_device(device_id)
        data = self.provider.get_current_device_reading(device_id, device.device_type.value)
        row = DeviceReading(
            device_id=data.device_id,
            recorded_at=data.recorded_at,
            power_w=data.power_w,
            voltage_v=data.voltage_v,
            current_a=data.current_a,
            status=data.status,
            source=data.source,
        )
        self.db.add(row)
        device.status = data.status
        device.last_seen_at = data.recorded_at
        self.db.commit()
        self.db.refresh(row)
        logger.info(
            "Recorded current device reading",
            extra={"context": {"device_id": str(device_id), "source": data.source.value}},
        )
        return row

    def get_historical_device_readings(
        self, device_id: uuid.UUID, start: datetime, end: datetime, interval_minutes: int
    ) -> List[DeviceReading]:
        device = self._require_device(device_id)

        existing = self.db.execute(
            select(DeviceReading)
            .where(DeviceReading.device_id == device_id)
            .where(DeviceReading.recorded_at >= start)
            .where(DeviceReading.recorded_at <= end)
            .order_by(DeviceReading.recorded_at)
        ).scalars().all()
        existing_timestamps = {row.recorded_at for row in existing}

        generated = self.provider.get_historical_device_readings(
            device_id, device.device_type.value, start, end, interval_minutes
        )
        missing = [d for d in generated if d.recorded_at not in existing_timestamps]

        new_rows = [
            DeviceReading(
                device_id=d.device_id,
                recorded_at=d.recorded_at,
                power_w=d.power_w,
                voltage_v=d.voltage_v,
                current_a=d.current_a,
                status=d.status,
                source=d.source,
            )
            for d in missing
        ]
        if new_rows:
            self.db.add_all(new_rows)
            self.db.commit()

        result = self.db.execute(
            select(DeviceReading)
            .where(DeviceReading.device_id == device_id)
            .where(DeviceReading.recorded_at >= start)
            .where(DeviceReading.recorded_at <= end)
            .order_by(DeviceReading.recorded_at)
        ).scalars().all()
        return list(result)

    # --- helpers ---

    def _require_microgrid(self, microgrid_id: uuid.UUID) -> Microgrid:
        microgrid = self.db.get(Microgrid, microgrid_id)
        if microgrid is None:
            raise NotFoundError(f"Microgrid {microgrid_id} not found.")
        return microgrid

    def _require_device(self, device_id: uuid.UUID) -> Device:
        device = self.db.get(Device, device_id)
        if device is None:
            raise NotFoundError(f"Device {device_id} not found.")
        return device
