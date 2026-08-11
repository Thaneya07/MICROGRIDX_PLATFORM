"""
Customer model.

Represents a customer profile, linked one-to-one with a User account and
associated with the microgrid it draws service from.
"""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    microgrid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("microgrids.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="customer")
    microgrid: Mapped["Microgrid"] = relationship("Microgrid", back_populates="customers")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="customer")
    loads: Mapped[list["Load"]] = relationship("Load", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Customer id={self.id} name={self.name}>"
