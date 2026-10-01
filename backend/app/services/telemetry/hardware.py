"""
Hardware telemetry provider.

Reads physical ESP32 telemetry that has already been persisted
to the PostgreSQL database by the hardware ingestion endpoint.
"""

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device import Device, DeviceStatus
from app.models.telemetry import (
    DeviceReading,
    EnergyReading,
    TelemetrySource,
)
from app.services.telemetry.base import (
    DeviceReadingData,
    EnergyReadingData,
    TelemetryProvider,
)


class HardwareTelemetryProvider(TelemetryProvider):
    """Telemetry provider backed by persisted physical hardware readings."""

    def __init__(self, db: Session):
        self.db = db

    def get_current_energy_reading(
        self,
        microgrid_id: uuid.UUID,
    ) -> EnergyReadingData:
        """Return the latest persisted hardware energy reading."""

        reading = self.db.scalar(
            select(EnergyReading)
            .where(
                EnergyReading.microgrid_id == microgrid_id,
                EnergyReading.source == TelemetrySource.HARDWARE,
            )
            .order_by(EnergyReading.recorded_at.desc())
            .limit(1)
        )

        if reading is None:
            raise ValueError(
                "No hardware energy telemetry is available "
                "for this microgrid."
            )

        return EnergyReadingData(
            microgrid_id=reading.microgrid_id,
            recorded_at=reading.recorded_at,
            consumption_w=reading.consumption_w,
            generation_w=reading.generation_w,
            grid_import_w=reading.grid_import_w,
            grid_export_w=reading.grid_export_w,
            available_energy_w=reading.available_energy_w,
            source=TelemetrySource.HARDWARE,
            battery_soc_percent=reading.battery_soc_percent,
            battery_power_w=reading.battery_power_w,
        )

    def get_historical_energy_readings(
        self,
        microgrid_id: uuid.UUID,
        start: datetime,
        end: datetime,
        interval_minutes: int,
    ) -> List[EnergyReadingData]:
        """Return persisted hardware energy readings in the requested range."""

        readings = self.db.scalars(
            select(EnergyReading)
            .where(
                EnergyReading.microgrid_id == microgrid_id,
                EnergyReading.source == TelemetrySource.HARDWARE,
                EnergyReading.recorded_at >= start,
                EnergyReading.recorded_at <= end,
            )
            .order_by(EnergyReading.recorded_at.asc())
        ).all()

        return [
            EnergyReadingData(
                microgrid_id=reading.microgrid_id,
                recorded_at=reading.recorded_at,
                consumption_w=reading.consumption_w,
                generation_w=reading.generation_w,
                grid_import_w=reading.grid_import_w,
                grid_export_w=reading.grid_export_w,
                available_energy_w=reading.available_energy_w,
                source=TelemetrySource.HARDWARE,
                battery_soc_percent=reading.battery_soc_percent,
                battery_power_w=reading.battery_power_w,
            )
            for reading in readings
        ]

    def get_current_device_reading(
        self,
        device_id: uuid.UUID,
        device_type: str,
    ) -> DeviceReadingData:
        """Return the latest persisted hardware reading for a device."""

        reading = self.db.scalar(
            select(DeviceReading)
            .where(
                DeviceReading.device_id == device_id,
                DeviceReading.source == TelemetrySource.HARDWARE,
            )
            .order_by(DeviceReading.recorded_at.desc())
            .limit(1)
        )

        if reading is None:
            raise ValueError(
                "No hardware telemetry is available "
                "for this device."
            )

        return DeviceReadingData(
            device_id=reading.device_id,
            recorded_at=reading.recorded_at,
            power_w=reading.power_w,
            voltage_v=reading.voltage_v,
            current_a=reading.current_a,
            status=reading.status,
            source=TelemetrySource.HARDWARE,
        )

    def get_historical_device_readings(
        self,
        device_id: uuid.UUID,
        device_type: str,
        start: datetime,
        end: datetime,
        interval_minutes: int,
    ) -> List[DeviceReadingData]:
        """Return persisted hardware device readings in the requested range."""

        readings = self.db.scalars(
            select(DeviceReading)
            .where(
                DeviceReading.device_id == device_id,
                DeviceReading.source == TelemetrySource.HARDWARE,
                DeviceReading.recorded_at >= start,
                DeviceReading.recorded_at <= end,
            )
            .order_by(DeviceReading.recorded_at.asc())
        ).all()

        return [
            DeviceReadingData(
                device_id=reading.device_id,
                recorded_at=reading.recorded_at,
                power_w=reading.power_w,
                voltage_v=reading.voltage_v,
                current_a=reading.current_a,
                status=reading.status,
                source=TelemetrySource.HARDWARE,
            )
            for reading in readings
        ]