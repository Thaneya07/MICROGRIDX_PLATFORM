import uuid

import pytest

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.device import Device
from app.models.load import Load
from app.models.microgrid import Microgrid
from app.models.telemetry import EnergyReading
from app.models.user import User
from app.services.demo.service import DEMO_MICROGRID_NAME, DEMO_USER_EMAIL, find_demo_microgrid


def _cleanup_demo(db):
    mg = find_demo_microgrid(db)
    if mg is None:
        return
    customers = db.query(Customer).filter(Customer.microgrid_id == mg.id).all()
    customer_ids = [c.id for c in customers]
    user_ids = [c.user_id for c in customers]
    db.query(Load).filter(Load.customer_id.in_(customer_ids)).delete(synchronize_session=False)
    db.query(Device).filter(Device.microgrid_id == mg.id).delete()
    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Customer).filter(Customer.microgrid_id == mg.id).delete()
    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()


@pytest.fixture(autouse=True)
def clean_demo_before_and_after():
    db = SessionLocal()
    _cleanup_demo(db)
    db.close()
    yield
    db = SessionLocal()
    _cleanup_demo(db)
    db.close()


def test_seed_demo_creates_full_microgrid(client):
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    body = response.json()
    assert body["already_existed"] is False
    assert body["microgrid"]["name"] == DEMO_MICROGRID_NAME
    assert body["readings_backfilled"] > 0

    db = SessionLocal()
    mg = find_demo_microgrid(db)
    assert mg is not None
    devices = db.query(Device).filter(Device.microgrid_id == mg.id).all()
    assert len(devices) == 5
    device_types = {d.device_type.value for d in devices}
    assert device_types == {"SOLAR_INVERTER", "BATTERY", "METER", "LOAD_CONTROLLER", "SENSOR"}

    customer = db.query(Customer).filter(Customer.microgrid_id == mg.id).first()
    loads = db.query(Load).filter(Load.customer_id == customer.id).all()
    assert len(loads) == 4
    db.close()


def test_seed_demo_is_idempotent(client):
    first = client.post("/api/demo/seed").json()
    second = client.post("/api/demo/seed").json()

    assert first["microgrid"]["id"] == second["microgrid"]["id"]
    assert first["already_existed"] is False
    assert second["already_existed"] is True

    db = SessionLocal()
    count = db.query(Microgrid).filter(Microgrid.name == DEMO_MICROGRID_NAME).count()
    assert count == 1
    db.close()


def test_seed_demo_readings_are_tagged_simulated(client):
    client.post("/api/demo/seed")
    db = SessionLocal()
    mg = find_demo_microgrid(db)
    readings = db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).all()
    assert len(readings) > 0
    assert all(r.source.value == "SIMULATED" for r in readings)
    db.close()


def test_list_microgrids_includes_seeded_demo(client):
    client.post("/api/demo/seed")
    response = client.get("/api/microgrids")
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert DEMO_MICROGRID_NAME in names


def test_list_microgrids_returns_valid_shape(client):
    response = client.get("/api/microgrids")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
