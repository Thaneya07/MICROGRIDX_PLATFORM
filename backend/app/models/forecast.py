"""
Forecast model metadata.

`ForecastModel` rows are the audit trail for trained forecasting models:
what was trained, on what data, when, with what evaluation results. The
serialized model itself (weights/tree ensemble) lives on disk at
`model_path`; this table never stores fabricated metrics — every value
here is written by `ForecastingService` immediately after running the
real train/validate/test pipeline in `app/services/forecasting`.
"""
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.telemetry import TelemetrySource


class ForecastTarget(str, enum.Enum):
    DEMAND = "DEMAND"
    SOLAR_GENERATION = "SOLAR_GENERATION"


class ForecastModelStatus(str, enum.Enum):
    TRAINED = "TRAINED"
    FAILED = "FAILED"


class ForecastModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Metadata for one trained forecasting model. The most recent `TRAINED`
    row for a given (microgrid_id, target, dataset_source) is the model
    served by the prediction API.
    """

    __tablename__ = "forecast_models"

    microgrid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("microgrids.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target: Mapped[ForecastTarget] = mapped_column(Enum(ForecastTarget, name="forecast_target"), nullable=False)
    dataset_source: Mapped[TelemetrySource] = mapped_column(
        Enum(TelemetrySource, name="telemetry_source", create_type=False), nullable=False
    )
    status: Mapped[ForecastModelStatus] = mapped_column(
        Enum(ForecastModelStatus, name="forecast_model_status"), nullable=False
    )

    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    algorithm_rationale: Mapped[str] = mapped_column(String(2000), nullable=False)

    feature_set: Mapped[dict] = mapped_column(JSON, nullable=False)

    training_start: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    training_end: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    n_train: Mapped[int] = mapped_column(Integer, nullable=False)
    n_validation: Mapped[int] = mapped_column(Integer, nullable=False)
    n_test: Mapped[int] = mapped_column(Integer, nullable=False)

    # Real, measured evaluation metrics (never fabricated): a JSON object of
    # {"validation": {...}, "test": {...}, "baseline_test": {...}}, each an
    # object of metric name -> float (mae, rmse, smape, r2 where defined).
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)

    model_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    microgrid: Mapped["Microgrid"] = relationship("Microgrid")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ForecastModel microgrid_id={self.microgrid_id} target={self.target} status={self.status}>"
