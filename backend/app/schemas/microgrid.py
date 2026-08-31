"""
Pydantic schemas for microgrid listing and the demo seed endpoint.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.microgrid import MicrogridStatus


class MicrogridSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    location: str
    status: MicrogridStatus
    created_at: datetime


class DemoSeedResponse(BaseModel):
    microgrid: MicrogridSummary
    already_existed: bool
    readings_backfilled: int
    message: str
