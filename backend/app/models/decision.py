"""
Decision (optimization result) model.

Stores the OUTPUT of one optimization run for a microgrid, not raw
telemetry — telemetry/forecast inputs are queried fresh from
EnergyReading/DeviceReading/ForecastModel each time a decision runs, per
the Phase 1 principle that time-series data stays out of core domain
tables. This table is the audit trail: what was recommended, why, under
what constraints, with what provenance.

IMPORTANT SAFETY NOTE (see app/services/decision/service.py for the full
architecture): a row in this table is a RECOMMENDATION, never a command.
Nothing in this codebase transmits these values to physical hardware.
"""
import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.telemetry import TelemetrySource


class OptimizationStatus(str, enum.Enum):
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    SAFE_FALLBACK = "SAFE_FALLBACK"
    ERROR = "ERROR"


class BatteryAction(str, enum.Enum):
    CHARGE = "CHARGE"
    DISCHARGE = "DISCHARGE"
    IDLE = "IDLE"


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Decision(UUIDPrimaryKeyMixin, Base):
    """One optimization run's recommendation for a microgrid, over a forecast horizon."""

    __tablename__ = "decisions"

    microgrid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("microgrids.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, server_default=text("clock_timestamp()")
    )

    source: Mapped[TelemetrySource] = mapped_column(
        Enum(TelemetrySource, name="telemetry_source", create_type=False), nullable=False
    )
    optimization_status: Mapped[OptimizationStatus] = mapped_column(
        Enum(OptimizationStatus, name="optimization_status"), nullable=False
    )

    horizon_start: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_end: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    objective_value: Mapped[float] = mapped_column(Float, nullable=True)

    recommended_battery_action: Mapped[BatteryAction] = mapped_column(
        Enum(BatteryAction, name="battery_action"), nullable=False
    )
    recommended_battery_power_w: Mapped[float] = mapped_column(Float, nullable=True)

    # List[{"load_id": str, "load_name": str, "action": str, "reason": str, "priority": int}]
    load_recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    expected_grid_import_wh: Mapped[float] = mapped_column(Float, nullable=True)
    expected_grid_export_wh: Mapped[float] = mapped_column(Float, nullable=True)
    expected_renewable_utilization_pct: Mapped[float] = mapped_column(Float, nullable=True)
    expected_peak_w: Mapped[float] = mapped_column(Float, nullable=True)

    # List[{"name": str, "satisfied": bool, "detail": str}]
    constraints_checked: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    constraints_satisfied: Mapped[bool] = mapped_column(Boolean, nullable=False)

    explanation: Mapped[str] = mapped_column(String(4000), nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(String(4000), nullable=False)

    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fallback_reason: Mapped[str] = mapped_column(String(2000), nullable=True)

    # {"demand_forecast_model_id": str|None, "solar_forecast_model_id": str|None, "solver": str, "solve_time_ms": float}
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    approval_status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status"), nullable=False, default=ApprovalStatus.PENDING
    )
    approved_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)

    microgrid: Mapped["Microgrid"] = relationship("Microgrid")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Decision microgrid_id={self.microgrid_id} status={self.optimization_status} action={self.recommended_battery_action}>"
