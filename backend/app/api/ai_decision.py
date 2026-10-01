from fastapi import APIRouter

from app.services.ai_decision_service import (
    generate_ai_decision,
)


router = APIRouter(
    prefix="/api/ai-decision",
    tags=["AI Decision Engine"],
)


@router.post("/generate")
def generate_decision(payload: dict):

    return generate_ai_decision(
        demand_forecast_w=payload[
            "demand_forecast_w"
        ],

        solar_forecast_w=payload[
            "solar_forecast_w"
        ],

        battery_soh_percent=payload[
            "battery_soh_percent"
        ],

        battery_rul_cycles=payload[
            "battery_rul_cycles"
        ],

        battery_status=payload[
            "battery_status"
        ],

        battery_risk_score=payload[
            "battery_risk_score"
        ],

        thermal_risk=payload[
            "thermal_risk"
        ],

        fault_class=payload[
            "fault_class"
        ],

        fault_severity=payload[
            "fault_severity"
        ],
    )