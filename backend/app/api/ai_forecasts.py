from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.ai_forecasting_service import (
    get_model_info,
    predict_demand,
    predict_solar,
    replay_demand,
    replay_solar,
)


router = APIRouter(
    prefix="/api/ai-forecasts",
    tags=["AI Forecasting"],
)


class ForecastRequest(BaseModel):
    features: dict[str, float] = Field(
        ...,
        description="Feature values required by the trained model.",
    )


@router.get("/models")
def models():

    return get_model_info()


@router.post("/demand")
def demand(request: ForecastRequest):

    try:
        return predict_demand(
            request.features
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post("/solar")
def solar(request: ForecastRequest):

    try:
        return predict_solar(
            request.features
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get("/replay/demand")
def demand_replay(
    points: int = Query(
        default=24,
        ge=1,
        le=288,
    ),
):

    try:
        return replay_demand(
            points=points
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get("/replay/solar")
def solar_replay(
    points: int = Query(
        default=144,
        ge=1,
        le=576,
    ),
):

    try:
        return replay_solar(
            points=points
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )