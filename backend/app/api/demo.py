"""
Demo/development seed API.

EXPLICIT, NAMED, DOCUMENTED — this never runs automatically. It exists
so a first-time user of the application can get a fully populated
example microgrid (devices, loads, backfilled SIMULATED telemetry)
without manually constructing one. Idempotent: calling POST
/api/demo/seed repeatedly returns the same demo microgrid rather than
creating duplicates.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.microgrid import DemoSeedResponse, MicrogridSummary
from app.services.demo.service import seed_demo_microgrid
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.dependencies import get_telemetry_provider

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed", response_model=DemoSeedResponse)
def seed_demo(
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(get_telemetry_provider),
) -> DemoSeedResponse:
    result = seed_demo_microgrid(db, provider)
    return DemoSeedResponse(
        microgrid=MicrogridSummary.model_validate(result.microgrid),
        already_existed=result.already_existed,
        readings_backfilled=result.readings_backfilled,
        message=result.message,
    )
