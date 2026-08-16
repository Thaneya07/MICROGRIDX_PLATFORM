"""
Forecasting API.

- POST /api/forecast/microgrids/{microgrid_id}/train
- GET  /api/forecast/microgrids/{microgrid_id}
- GET  /api/forecast/microgrids/{microgrid_id}/models

Training is a deliberate, explicit action (never triggered implicitly by
a prediction request) so it's always clear when a model was (re)trained
and on what data. Authentication/authorization is not yet implemented
(deferred to a later step); these endpoints are unauthenticated in this
phase.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.errors import NotFoundError
from app.models.forecast import ForecastTarget
from app.models.telemetry import TelemetrySource
from app.schemas.forecast import (
    ForecastModelSummaryResponse,
    ForecastPointResponse,
    ForecastResponse,
    TrainForecastResponse,
)
from app.services.forecasting.service import ForecastingService

router = APIRouter(prefix="/api/forecast", tags=["forecasting"])


def get_forecasting_service(db: Session = Depends(get_db)) -> ForecastingService:
    return ForecastingService(db)


@router.post("/microgrids/{microgrid_id}/train", response_model=TrainForecastResponse)
def train_forecast_model(
    microgrid_id: uuid.UUID,
    target: ForecastTarget = Query(...),
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: ForecastingService = Depends(get_forecasting_service),
) -> TrainForecastResponse:
    model_row = service.train(microgrid_id, target, source)
    return TrainForecastResponse.model_validate(model_row)


@router.get("/microgrids/{microgrid_id}", response_model=ForecastResponse)
def get_forecast(
    microgrid_id: uuid.UUID,
    target: ForecastTarget = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    interval_minutes: int = Query(default=30, ge=1, le=1440),
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: ForecastingService = Depends(get_forecasting_service),
) -> ForecastResponse:
    model_row = service.get_latest_model(microgrid_id, target, source)
    if model_row is None:
        raise NotFoundError(
            f"No trained {target.value} forecasting model exists yet for this microgrid/source. "
            f"POST /api/forecast/microgrids/{microgrid_id}/train first."
        )
    points = service.predict(microgrid_id, target, source, start, end, interval_minutes)

    return ForecastResponse(
        microgrid_id=microgrid_id,
        target=target,
        dataset_source=source,
        model_id=model_row.id,
        model_trained_at=model_row.created_at,
        start=start,
        end=end,
        interval_minutes=interval_minutes,
        points=[
            ForecastPointResponse(
                timestamp=p.timestamp,
                predicted_w=round(p.prediction.mean, 2),
                lower_95_w=round(p.prediction.lower_95, 2),
                upper_95_w=round(p.prediction.upper_95, 2),
            )
            for p in points
        ],
    )


@router.get("/microgrids/{microgrid_id}/models", response_model=List[ForecastModelSummaryResponse])
def list_forecast_models(
    microgrid_id: uuid.UUID,
    target: Optional[ForecastTarget] = Query(default=None),
    service: ForecastingService = Depends(get_forecasting_service),
) -> List[ForecastModelSummaryResponse]:
    rows = service.list_models(microgrid_id, target)
    return [ForecastModelSummaryResponse.model_validate(r) for r in rows]
