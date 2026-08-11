"""
Foundational Pydantic schemas for domain entities.

These are minimal read-oriented schemas intended to validate/serialize the
Phase 1 domain models. Write/create schemas, pagination, and full CRUD
endpoints are deferred to a later phase — Phase 1 only needs the models to
exist and be exercisable through the ORM and migrations.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole
from app.models.microgrid import MicrogridStatus
from app.models.device import DeviceType, DeviceStatus
from app.models.load import LoadCategory, LoadControlMode, LoadStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MicrogridRead(ORMModel):
    id: uuid.UUID
    name: str
    location: str
    status: MicrogridStatus
    created_at: datetime
    updated_at: datetime


class CustomerRead(ORMModel):
    id: uuid.UUID
    user_id: uuid.UUID
    microgrid_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class DeviceRead(ORMModel):
    id: uuid.UUID
    microgrid_id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    device_type: DeviceType
    status: DeviceStatus
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class LoadRead(ORMModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    name: str
    category: LoadCategory
    priority: int
    controllable: bool
    control_mode: LoadControlMode
    status: LoadStatus
    created_at: datetime
    updated_at: datetime
