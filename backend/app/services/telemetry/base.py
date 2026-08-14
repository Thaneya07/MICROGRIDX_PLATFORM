"""
Telemetry provider contract.

`TelemetryProvider` is the single interface the rest of the application
depends on for obtaining energy/device readings. `SimulationTelemetryProvider`
implements it today; a future `HardwareTelemetryProvider` (e.g. reading from
ESP32 devices over MQTT/HTTP) implements the same interface so that no API
route, service, or downstream consumer (analytics, decisions) needs to
change when real hardware is introduced — only the configured provider
changes.
"""
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.models.device import DeviceStatus
from app.models.telemetry import TelemetrySource


@dataclass(frozen=True)
class EnergyReadingData:
    """Provider-agnostic representation of a microgrid-level energy snapshot."""

    microgrid_id: uuid.UUID
    recorded_at: datetime
    consumption_w: float
    generation_w: float
    grid_import_w: float
    grid_export_w: float
    available_energy_w: float
    source: TelemetrySource
    battery_soc_percent: Optional[float] = None
    battery_power_w: Optional[float] = None


@dataclass(frozen=True)
class DeviceReadingData:
    """Provider-agnostic representation of a device-level telemetry snapshot."""

    device_id: uuid.UUID
    recorded_at: datetime
    power_w: float
    voltage_v: float
    current_a: float
    status: DeviceStatus
    source: TelemetrySource


class TelemetryProvider(ABC):
    """Contract every telemetry provider (simulated or hardware) must implement."""

    @abstractmethod
    def get_current_energy_reading(self, microgrid_id: uuid.UUID) -> EnergyReadingData:
        """Return the current energy snapshot for a microgrid."""
        raise NotImplementedError

    @abstractmethod
    def get_historical_energy_readings(
        self,
        microgrid_id: uuid.UUID,
        start: datetime,
        end: datetime,
        interval_minutes: int,
    ) -> List[EnergyReadingData]:
        """Return energy snapshots for a microgrid across a time range at a fixed interval."""
        raise NotImplementedError

    @abstractmethod
    def get_current_device_reading(self, device_id: uuid.UUID, device_type: str) -> DeviceReadingData:
        """Return the current telemetry snapshot for a single device."""
        raise NotImplementedError

    @abstractmethod
    def get_historical_device_readings(
        self,
        device_id: uuid.UUID,
        device_type: str,
        start: datetime,
        end: datetime,
        interval_minutes: int,
    ) -> List[DeviceReadingData]:
        """Return telemetry snapshots for a device across a time range at a fixed interval."""
        raise NotImplementedError
