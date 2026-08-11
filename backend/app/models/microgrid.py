"""
Microgrid model.

Represents a physical/logical microgrid installation that customers and
devices belong to.
"""
import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MicrogridStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class Microgrid(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "microgrids"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[MicrogridStatus] = mapped_column(
        Enum(MicrogridStatus, name="microgrid_status"),
        nullable=False,
        default=MicrogridStatus.ACTIVE,
    )

    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="microgrid")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="microgrid")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Microgrid id={self.id} name={self.name} status={self.status}>"
