from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.battery_health.service import (
    predict_battery_health,
)


router = APIRouter(
    prefix="/api/battery-health",
    tags=["Battery Health"],
)


class BatteryHealthRequest(BaseModel):
    ambient_temperature: float

    voltage_mean: float
    voltage_min: float
    voltage_max: float
    voltage_std: float

    current_mean: float
    current_min: float
    current_max: float
    current_std: float

    temperature_mean: float
    temperature_min: float
    temperature_max: float
    temperature_std: float

    duration_sec: float

    current_load_mean: float
    voltage_load_mean: float

    discharge_cycle_index: float


@router.post("/predict")
def predict(request: BatteryHealthRequest):

    try:

        features = request.model_dump()

        result = predict_battery_health(
            features
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )