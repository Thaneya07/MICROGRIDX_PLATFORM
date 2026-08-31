"""
Pydantic schemas for the Decision Engine API.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.decision import ApprovalStatus, BatteryAction, OptimizationStatus
from app.services.decision_engine import OperatingMode
from app.models.telemetry import TelemetrySource


class LoadRecommendationResponse(BaseModel):
    load_id: str
    load_name: str
    action: str
    reason: str
    priority: int


class ConstraintCheckResponse(BaseModel):
    name: str
    satisfied: bool
    detail: str


class DecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    microgrid_id: uuid.UUID
    created_at: datetime
    source: TelemetrySource
    optimization_status: OptimizationStatus
    operating_mode: OperatingMode
    operating_mode_reason: str

    horizon_start: datetime
    horizon_end: datetime
    interval_minutes: int

    objective_value: Optional[float]

    recommended_battery_action: BatteryAction
    recommended_battery_power_w: Optional[float]
    load_recommendations: List[LoadRecommendationResponse]

    expected_grid_import_wh: Optional[float]
    expected_grid_export_wh: Optional[float]
    expected_renewable_utilization_pct: Optional[float]
    expected_peak_w: Optional[float]

    constraints_checked: List[ConstraintCheckResponse]
    constraints_satisfied: bool

    explanation: str
    recommendation_reason: str

    fallback_used: bool
    fallback_reason: Optional[str]

    provenance: Dict

    approval_status: ApprovalStatus
    approved_at: Optional[datetime]

    safety_note: str = Field(
        default=(
            "This is a decision-support recommendation only. MicroGridX does not automatically "
            "actuate physical hardware; no command has been sent to any device."
        )
    )


class ApprovalRequest(BaseModel):
    approved: bool
