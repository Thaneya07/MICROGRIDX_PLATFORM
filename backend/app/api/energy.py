"""
Energy analytics API.

- GET /api/energy/microgrids/{microgrid_id}/summary
- GET /api/energy/microgrids/{microgrid_id}/patterns
- GET /api/energy/microgrids/{microgrid_id}/profile

All three read exclusively from persisted telemetry (never live-generate
data) and operate on a single explicit `TelemetrySource` at a time so
simulated and hardware readings are never blended into one aggregate.
Authentication/authorization is not yet implemented (deferred to a later
step); these endpoints are unauthenticated in this phase.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.telemetry import TelemetrySource
from app.schemas.analytics import (
    ConsumptionPatternsResponse,
    CustomerEnergyProfileResponse,
    EnergySummaryResponse,
)
from app.services.analytics.service import AnalyticsService

router = APIRouter(prefix="/api/energy", tags=["energy-analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/microgrids/{microgrid_id}/summary", response_model=EnergySummaryResponse)
def get_energy_summary(
    microgrid_id: uuid.UUID,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: AnalyticsService = Depends(get_analytics_service),
) -> EnergySummaryResponse:
    summary = service.get_energy_summary(microgrid_id, start, end, source)
    return EnergySummaryResponse.model_validate(summary)


@router.get("/microgrids/{microgrid_id}/patterns", response_model=ConsumptionPatternsResponse)
def get_consumption_patterns(
    microgrid_id: uuid.UUID,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ConsumptionPatternsResponse:
    patterns = service.get_consumption_patterns(microgrid_id, start, end, source)
    return ConsumptionPatternsResponse.model_validate(patterns)


@router.get("/microgrids/{microgrid_id}/profile", response_model=CustomerEnergyProfileResponse)
def get_energy_profile(
    microgrid_id: uuid.UUID,
    start: Optional[datetime] = Query(default=None),
    end: Optional[datetime] = Query(default=None),
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: AnalyticsService = Depends(get_analytics_service),
) -> CustomerEnergyProfileResponse:
    profile = service.get_energy_profile(microgrid_id, start, end, source)
    return CustomerEnergyProfileResponse.model_validate(profile)
