"""
Load model.

Represents a controllable or non-controllable electrical load belonging
to a customer (e.g. HVAC, water heater, EV charger). Actual load-shifting
decisions are made later by the Decision Engine (Phase 2+); this model
only captures the foundational domain data.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LoadCategory(str, enum.Enum):
    HVAC = "HVAC"
    WATER_HEATER = "WATER_HEATER"
    EV_CHARGER = "EV_CHARGER"
    LIGHTING = "LIGHTING"
    APPLIANCE = "APPLIANCE"
    OTHER = "OTHER"


class LoadControlMode(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class LoadStatus(str, enum.Enum):
    ON = "ON"
    OFF = "OFF"
    UNKNOWN = "UNKNOWN"


class Load(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loads"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[LoadCategory] = mapped_column(Enum(LoadCategory, name="load_category"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controllable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    control_mode: Mapped[LoadControlMode] = mapped_column(
        Enum(LoadControlMode, name="load_control_mode"), nullable=False, default=LoadControlMode.MANUAL
    )
    status: Mapped[LoadStatus] = mapped_column(
        Enum(LoadStatus, name="load_status"), nullable=False, default=LoadStatus.UNKNOWN
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="loads")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Load id={self.id} name={self.name} category={self.category}>"
