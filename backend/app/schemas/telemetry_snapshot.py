"""
Microgrid snapshot schemas (Step 6: 3D visualization).

A "snapshot" combines everything the 3D scene needs to render one frame:
the microgrid's current energy reading, every device's current reading
(tagged with its `device_type` so the frontend can route it to the right
mesh — solar array, battery, meter, load controller, sensor), and the
microgrid's loads (which have no telemetry of their own by design — see
Phase 1 — so only their static configured state is included).

This is the single DTO shape used by both the REST snapshot endpoint and
the WebSocket stream, and by both `SimulationTelemetryProvider` and (once
implemented) `HardwareTelemetryProvider` — the frontend 3D scene depends
on this shape, never on which provider produced it, other than reading
the explicit `source` field.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.device import DeviceStatus, DeviceType
from app.models.load import LoadCategory, LoadControlMode, LoadStatus
from app.models.microgrid import MicrogridStatus
from app.models.telemetry import TelemetrySource
from app.schemas.telemetry import EnergyReadingRead


class DeviceSnapshotReading(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: uuid.UUID
    device_type: DeviceType
    status: DeviceStatus
    recorded_at: datetime
    power_w: float
    voltage_v: float
    current_a: float
    source: TelemetrySource


class LoadSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    load_id: uuid.UUID
    name: str
    category: LoadCategory
    priority: int
    controllable: bool
    control_mode: LoadControlMode
    status: LoadStatus


class MicrogridSnapshot(BaseModel):
    microgrid_id: uuid.UUID
    name: str
    location: str
    status: MicrogridStatus

    server_time: datetime
    source: TelemetrySource

    energy_reading: Optional[EnergyReadingRead]
    devices: List[DeviceSnapshotReading]
    loads: List[LoadSnapshot]

    # Explicit so the 3D scene never has to guess: absence of a reading
    # (e.g. transient provider error) is representable without inventing
    # a value.
    energy_reading_error: Optional[str] = None
