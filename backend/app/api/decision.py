"""
Decision Engine / Optimization API.

- POST /api/decision/microgrids/{id}/optimize   run a new optimization
- GET  /api/decision/microgrids/{id}/latest      most recent decision
- GET  /api/decision/microgrids/{id}/history      recent decision history
- POST /api/decision/{decision_id}/approve        record human approval/rejection

SAFETY: every endpoint here returns or records a RECOMMENDATION. None of
them send any command to physical hardware — see
app/services/decision/service.py and docs/architecture for the full
safety boundary. Authentication/authorization is not yet implemented
(deferred, consistent with all other API modules in this project);
these endpoints are unauthenticated in this phase.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.connection import get_db
from app.models.telemetry import TelemetrySource
from app.schemas.decision import ApprovalRequest, DecisionResponse
from app.services.decision.service import DecisionService
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.dependencies import get_telemetry_provider

router = APIRouter(prefix="/api/decision", tags=["decision"])


def get_decision_service(
    db: Session = Depends(get_db),
    provider: TelemetryProvider = Depends(get_telemetry_provider),
) -> DecisionService:
    return DecisionService(db, provider)


@router.post("/microgrids/{microgrid_id}/optimize", response_model=DecisionResponse)
def optimize(
    microgrid_id: uuid.UUID,
    source: TelemetrySource = Query(default=TelemetrySource.SIMULATED),
    service: DecisionService = Depends(get_decision_service),
) -> DecisionResponse:
    decision = service.optimize(microgrid_id, source)
    return DecisionResponse.model_validate(decision)


@router.get("/microgrids/{microgrid_id}/latest", response_model=DecisionResponse)
def get_latest(
    microgrid_id: uuid.UUID,
    service: DecisionService = Depends(get_decision_service),
) -> DecisionResponse:
    decision = service.get_latest(microgrid_id)
    if decision is None:
        raise NotFoundError(
            f"No decision exists yet for microgrid {microgrid_id}. "
            f"POST /api/decision/microgrids/{microgrid_id}/optimize first."
        )
    return DecisionResponse.model_validate(decision)


@router.get("/microgrids/{microgrid_id}/history", response_model=List[DecisionResponse])
def get_history(
    microgrid_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    service: DecisionService = Depends(get_decision_service),
) -> List[DecisionResponse]:
    decisions = service.list_history(microgrid_id, limit)
    return [DecisionResponse.model_validate(d) for d in decisions]


@router.post("/{decision_id}/approve", response_model=DecisionResponse)
def approve(
    decision_id: uuid.UUID,
    body: ApprovalRequest,
    service: DecisionService = Depends(get_decision_service),
) -> DecisionResponse:
    """
    Records human approval/rejection of a recommendation. This ONLY
    updates a database field — it never triggers any hardware action.
    """
    decision = service.set_approval(decision_id, body.approved)
    return DecisionResponse.model_validate(decision)
