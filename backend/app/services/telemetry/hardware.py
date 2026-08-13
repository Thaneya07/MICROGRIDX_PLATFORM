"""
Hardware telemetry provider (future work).

Not implemented in this phase. Exists so the `TelemetryProvider` contract
has a concrete placeholder showing where real hardware ingestion (e.g.
ESP32 devices reporting over MQTT/HTTP) will plug in without changing the
API or business logic that depends on `TelemetryProvider`.
"""
import uuid
from datetime import datetime
from typing import List

from app.models.device import DeviceStatus
from app.services.telemetry.base import DeviceReadingData, EnergyReadingData, TelemetryProvider


class HardwareTelemetryProvider(TelemetryProvider):
    """Placeholder for a real-sensor-backed telemetry provider. Not implemented yet."""

    def get_current_energy_reading(self, microgrid_id: uuid.UUID) -> EnergyReadingData:
        raise NotImplementedError(
            "HardwareTelemetryProvider is not implemented yet. Configure "
            "TELEMETRY_PROVIDER=simulation until real sensor ingestion is built."
        )

    def get_historical_energy_readings(
        self, microgrid_id: uuid.UUID, start: datetime, end: datetime, interval_minutes: int
    ) -> List[EnergyReadingData]:
        raise NotImplementedError(
            "HardwareTelemetryProvider is not implemented yet. Historical hardware readings "
            "must instead be queried from the database once ingestion exists."
        )

    def get_current_device_reading(self, device_id: uuid.UUID, device_type: str) -> DeviceReadingData:
        raise NotImplementedError("HardwareTelemetryProvider is not implemented yet.")

    def get_historical_device_readings(
        self, device_id: uuid.UUID, device_type: str, start: datetime, end: datetime, interval_minutes: int
    ) -> List[DeviceReadingData]:
        raise NotImplementedError("HardwareTelemetryProvider is not implemented yet.")
