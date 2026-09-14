"""
Pydantic schemas for telemetry endpoints.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.device import DeviceStatus
from app.models.telemetry import TelemetrySource


class EnergyReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    microgrid_id: uuid.UUID
    recorded_at: datetime
    consumption_w: float
    generation_w: float
    grid_import_w: float
    grid_export_w: float
    available_energy_w: float
    battery_soc_percent: Optional[float]
    battery_power_w: Optional[float]
    source: TelemetrySource

    @field_validator("recorded_at")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class EnergyReadingHistoryResponse(BaseModel):
    microgrid_id: uuid.UUID
    start: datetime
    end: datetime
    interval_minutes: int
    readings: List[EnergyReadingRead]


class DeviceReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    recorded_at: datetime
    power_w: float
    voltage_v: float
    current_a: float
    status: DeviceStatus
    source: TelemetrySource

    @field_validator("recorded_at")
    @classmethod
    def normalize_recorded_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class DeviceReadingHistoryResponse(BaseModel):
    device_id: uuid.UUID
    start: datetime
    end: datetime
    interval_minutes: int
    readings: List[DeviceReadingRead]


class HistoryQueryParams(BaseModel):
    """Shared validation for historical telemetry queries."""

    start: datetime
    end: datetime
    interval_minutes: int = Field(default=15, ge=1, le=1440)

    @model_validator(mode="after")
    def _validate_range(self) -> "HistoryQueryParams":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self