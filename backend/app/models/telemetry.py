"""
Telemetry models.

Time-series energy data is deliberately kept in its own tables, separate
from the core domain entities (Microgrid, Device) defined in Phase 1. This
keeps the core tables small and stable while telemetry volume grows
independently, and allows telemetry tables to be partitioned/archived in
the future without touching domain tables.

Every row is tagged with a `TelemetrySource` so simulated data can never be
mistaken for a real hardware reading, in the API or downstream.
"""
import enum
import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.device import DeviceStatus


class TelemetrySource(str, enum.Enum):
    """Identifies where a telemetry row came from. Never inferred, always explicit."""

    SIMULATED = "SIMULATED"
    HARDWARE = "HARDWARE"


class EnergyReading(UUIDPrimaryKeyMixin, Base):
    """
    A microgrid-level energy snapshot at a point in time: total consumption,
    renewable generation, grid import/export, available energy, and (where
    applicable) battery state of charge and signed battery power flow.

    `battery_power_w` is signed: positive means the battery is discharging
    (supplying power to the microgrid), negative means it is charging
    (drawing power). Together with `consumption_w`, `generation_w`,
    `grid_import_w`, and `grid_export_w`, it must satisfy the power-balance
    invariant enforced by the telemetry provider at write time:

        generation_w + max(0, battery_power_w) + grid_import_w
            == consumption_w + max(0, -battery_power_w) + grid_export_w
    """

    __tablename__ = "energy_readings"
    __table_args__ = (
        Index("ix_energy_readings_microgrid_recorded_at", "microgrid_id", "recorded_at"),
        UniqueConstraint(
            "microgrid_id", "recorded_at", "source", name="uq_energy_readings_microgrid_recorded_source"
        ),
        CheckConstraint("consumption_w >= 0", name="ck_energy_readings_consumption_non_negative"),
        CheckConstraint("generation_w >= 0", name="ck_energy_readings_generation_non_negative"),
        CheckConstraint("grid_import_w >= 0", name="ck_energy_readings_grid_import_non_negative"),
        CheckConstraint("grid_export_w >= 0", name="ck_energy_readings_grid_export_non_negative"),
        CheckConstraint("available_energy_w >= 0", name="ck_energy_readings_available_energy_non_negative"),
        CheckConstraint(
            "battery_soc_percent IS NULL OR (battery_soc_percent >= 0 AND battery_soc_percent <= 100)",
            name="ck_energy_readings_battery_soc_range",
        ),
    )

    microgrid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("microgrids.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    consumption_w: Mapped[float] = mapped_column(Float, nullable=False)
    generation_w: Mapped[float] = mapped_column(Float, nullable=False)
    grid_import_w: Mapped[float] = mapped_column(Float, nullable=False)
    grid_export_w: Mapped[float] = mapped_column(Float, nullable=False)
    available_energy_w: Mapped[float] = mapped_column(Float, nullable=False)
    battery_soc_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_power_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    source: Mapped[TelemetrySource] = mapped_column(
        Enum(TelemetrySource, name="telemetry_source"), nullable=False
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    microgrid: Mapped["Microgrid"] = relationship("Microgrid")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EnergyReading microgrid_id={self.microgrid_id} recorded_at={self.recorded_at} source={self.source}>"


class DeviceReading(UUIDPrimaryKeyMixin, Base):
    """
    A device-level telemetry snapshot: instantaneous power/voltage/current
    and reported device status at a point in time.
    """

    __tablename__ = "device_readings"
    __table_args__ = (
        Index("ix_device_readings_device_recorded_at", "device_id", "recorded_at"),
        UniqueConstraint(
            "device_id", "recorded_at", "source", name="uq_device_readings_device_recorded_source"
        ),
        CheckConstraint("power_w >= 0", name="ck_device_readings_power_non_negative"),
        CheckConstraint("voltage_v >= 0", name="ck_device_readings_voltage_non_negative"),
        CheckConstraint("current_a >= 0", name="ck_device_readings_current_non_negative"),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recorded_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    power_w: Mapped[float] = mapped_column(Float, nullable=False)
    voltage_v: Mapped[float] = mapped_column(Float, nullable=False)
    current_a: Mapped[float] = mapped_column(Float, nullable=False)

    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status", create_type=False), nullable=False
    )

    source: Mapped[TelemetrySource] = mapped_column(
        Enum(TelemetrySource, name="telemetry_source", create_type=False), nullable=False
    )

    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    device: Mapped["Device"] = relationship("Device")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DeviceReading device_id={self.device_id} recorded_at={self.recorded_at} source={self.source}>"
