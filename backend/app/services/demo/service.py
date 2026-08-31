"""
Demo/development seed mechanism.

EXPLICIT AND DOCUMENTED, PER PROJECT POLICY: this module never creates
data silently. It only runs when a user (or the frontend, on the user's
explicit "Load demo microgrid" click) calls `POST /api/demo/seed`. It is
idempotent — calling it again returns the existing demo microgrid rather
than creating a duplicate — identified by a fixed, clearly-labeled name
(`DEMO_MICROGRID_NAME`) so it is always distinguishable from real
customer data in the database.

All telemetry backfilled here goes through the existing, unmodified
`TelemetryService` / `SimulationTelemetryProvider` — this module does
not fabricate readings itself, it only decides which historical window
to backfill and persists it via the same code path every other
telemetry endpoint uses.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.device import Device, DeviceStatus, DeviceType
from app.models.load import Load, LoadCategory, LoadControlMode, LoadStatus
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import TelemetrySource
from app.models.user import User, UserRole
from app.services.telemetry.base import TelemetryProvider
from app.services.telemetry.service import TelemetryService

DEMO_MICROGRID_NAME = "MicroGridX Demo Site"
DEMO_MICROGRID_LOCATION = "Demo (simulated data)"
DEMO_USER_EMAIL = "demo@microgridx.local"
DEMO_BACKFILL_DAYS = 10
DEMO_BACKFILL_INTERVAL_MINUTES = 60


@dataclass
class DemoSeedResult:
    microgrid: Microgrid
    already_existed: bool
    readings_backfilled: int
    message: str


def find_demo_microgrid(db: Session) -> Optional[Microgrid]:
    return db.execute(select(Microgrid).where(Microgrid.name == DEMO_MICROGRID_NAME)).scalars().first()


def seed_demo_microgrid(db: Session, provider: TelemetryProvider) -> DemoSeedResult:
    existing = find_demo_microgrid(db)
    if existing is not None:
        return DemoSeedResult(
            microgrid=existing,
            already_existed=True,
            readings_backfilled=0,
            message="Demo microgrid already exists; returning it unchanged.",
        )

    microgrid = Microgrid(name=DEMO_MICROGRID_NAME, location=DEMO_MICROGRID_LOCATION, status=MicrogridStatus.ACTIVE)
    db.add(microgrid)
    db.commit()
    db.refresh(microgrid)

    user = db.execute(select(User).where(User.email == DEMO_USER_EMAIL)).scalars().first()
    if user is None:
        user = User(email=DEMO_USER_EMAIL, password_hash="demo-not-a-real-account", role=UserRole.CUSTOMER, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    customer = Customer(user_id=user.id, microgrid_id=microgrid.id, name="Demo Customer")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    devices = [
        Device(microgrid_id=microgrid.id, device_type=DeviceType.SOLAR_INVERTER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=microgrid.id, device_type=DeviceType.BATTERY, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=microgrid.id, device_type=DeviceType.METER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=microgrid.id, device_type=DeviceType.LOAD_CONTROLLER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=microgrid.id, device_type=DeviceType.SENSOR, status=DeviceStatus.OFFLINE),
    ]
    db.add_all(devices)
    db.commit()

    loads = [
        Load(customer_id=customer.id, name="EV Charger", category=LoadCategory.EV_CHARGER, priority=1,
             controllable=True, control_mode=LoadControlMode.AUTOMATIC, status=LoadStatus.ON),
        Load(customer_id=customer.id, name="Pool Pump", category=LoadCategory.OTHER, priority=3,
             controllable=True, control_mode=LoadControlMode.AUTOMATIC, status=LoadStatus.OFF),
        Load(customer_id=customer.id, name="Water Heater", category=LoadCategory.WATER_HEATER, priority=5,
             controllable=True, control_mode=LoadControlMode.AUTOMATIC, status=LoadStatus.ON),
        Load(customer_id=customer.id, name="Refrigerator", category=LoadCategory.APPLIANCE, priority=10,
             controllable=False, control_mode=LoadControlMode.MANUAL, status=LoadStatus.ON),
    ]
    db.add_all(loads)
    db.commit()

    telemetry_service = TelemetryService(db, provider)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DEMO_BACKFILL_DAYS)
    readings = telemetry_service.get_historical_energy_readings(
        microgrid.id, start, end, DEMO_BACKFILL_INTERVAL_MINUTES
    )

    return DemoSeedResult(
        microgrid=microgrid,
        already_existed=False,
        readings_backfilled=len(readings),
        message=f"Created demo microgrid with 5 devices, 4 loads, and {len(readings)} backfilled "
        f"{TelemetrySource.SIMULATED.value} energy readings covering the last {DEMO_BACKFILL_DAYS} days.",
    )
