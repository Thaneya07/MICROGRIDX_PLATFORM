from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.fault_detection.service import (
    predict_fault,
)


router = APIRouter(
    prefix="/api/fault-detection",
    tags=["Fault Detection"],
)


class FaultDetectionRequest(BaseModel):
    EA: float
    EB: float
    EC: float


@router.post("/predict")
def predict(request: FaultDetectionRequest):

    try:

        return predict_fault(
            request.model_dump()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )