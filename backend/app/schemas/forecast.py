"""
Pydantic schemas for forecasting endpoints.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.forecast import ForecastModelStatus, ForecastTarget
from app.models.telemetry import TelemetrySource


class RegressionMetricsResponse(BaseModel):
    mae: float
    rmse: float
    smape: Optional[float]
    r2: Optional[float]
    n: int


class TrainForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    microgrid_id: uuid.UUID
    target: ForecastTarget
    dataset_source: TelemetrySource
    status: ForecastModelStatus
    algorithm: str
    algorithm_rationale: str
    feature_set: List[str]
    training_start: datetime
    training_end: datetime
    n_train: int
    n_validation: int
    n_test: int
    metrics: Dict[str, Dict]
    created_at: datetime

    data_provenance_note: str = Field(
        default=(
            "Trained and evaluated on SIMULATED telemetry only. Metrics reflect performance "
            "on this simulation, not on real hardware sensor data — treat as DEMO/SIMULATION "
            "results, not validated real-world accuracy."
        )
    )


class ForecastModelSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target: ForecastTarget
    dataset_source: TelemetrySource
    status: ForecastModelStatus
    algorithm: str
    n_train: int
    n_validation: int
    n_test: int
    metrics: Dict[str, Dict]
    created_at: datetime


class ForecastPointResponse(BaseModel):
    timestamp: datetime
    predicted_w: float
    lower_95_w: float
    upper_95_w: float


class ForecastResponse(BaseModel):
    microgrid_id: uuid.UUID
    target: ForecastTarget
    dataset_source: TelemetrySource
    model_id: uuid.UUID
    model_trained_at: datetime
    start: datetime
    end: datetime
    interval_minutes: int
    points: List[ForecastPointResponse]

    data_provenance_note: str = Field(
        default=(
            "FORECAST data: model output, not a live or historical sensor reading. "
            "The underlying model was trained on SIMULATED telemetry — treat these values as "
            "DEMO/SIMULATION forecasts, not validated real-world predictions. "
            "Uncertainty bands are an approximation derived from ensemble spread, not a "
            "statistically calibrated confidence interval."
        )
    )
