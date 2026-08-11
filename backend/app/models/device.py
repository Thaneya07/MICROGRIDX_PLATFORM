"""
Device model.

Represents a physical device (e.g. inverter, meter, battery, sensor)
installed within a microgrid, optionally attributed to a specific
customer.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceType(str, enum.Enum):
    METER = "METER"
    SOLAR_INVERTER = "SOLAR_INVERTER"
    BATTERY = "BATTERY"
    LOAD_CONTROLLER = "LOAD_CONTROLLER"
    SENSOR = "SENSOR"
    OTHER = "OTHER"


class DeviceStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    FAULT = "FAULT"
    DECOMMISSIONED = "DECOMMISSIONED"


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    microgrid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("microgrids.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType, name="device_type"), nullable=False)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, name="device_status"), nullable=False, default=DeviceStatus.OFFLINE
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    microgrid: Mapped["Microgrid"] = relationship("Microgrid", back_populates="devices")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="devices")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Device id={self.id} type={self.device_type} status={self.status}>"
