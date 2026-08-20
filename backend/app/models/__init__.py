"""
Aggregates all ORM models so that `Base.metadata` is fully populated for
Alembic autogeneration and application startup.
"""
from app.database.base import Base  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.microgrid import Microgrid, MicrogridStatus  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.device import Device, DeviceType, DeviceStatus  # noqa: F401
from app.models.load import Load, LoadCategory, LoadControlMode, LoadStatus  # noqa: F401
from app.models.telemetry import EnergyReading, DeviceReading, TelemetrySource  # noqa: F401
from app.models.forecast import ForecastModel, ForecastTarget, ForecastModelStatus  # noqa: F401
from app.models.decision import Decision, OptimizationStatus, BatteryAction, ApprovalStatus  # noqa: F401

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Microgrid",
    "MicrogridStatus",
    "Customer",
    "Device",
    "DeviceType",
    "DeviceStatus",
    "Load",
    "LoadCategory",
    "LoadControlMode",
    "LoadStatus",
    "EnergyReading",
    "DeviceReading",
    "TelemetrySource",
    "ForecastModel",
    "ForecastTarget",
    "ForecastModelStatus",
    "Decision",
    "OptimizationStatus",
    "BatteryAction",
    "ApprovalStatus",
]
