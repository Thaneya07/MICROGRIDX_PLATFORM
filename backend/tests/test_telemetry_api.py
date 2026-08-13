import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.device import Device, DeviceStatus, DeviceType
from app.models.microgrid import Microgrid, MicrogridStatus


@pytest.fixture()
def microgrid_and_device():
    db = SessionLocal()
    microgrid = Microgrid(
        name=f"test-microgrid-{uuid.uuid4()}",
        location="Test Site",
        status=MicrogridStatus.ACTIVE,
    )
    db.add(microgrid)
    db.commit()
    db.refresh(microgrid)

    device = Device(
        microgrid_id=microgrid.id,
        device_type=DeviceType.SOLAR_INVERTER,
        status=DeviceStatus.OFFLINE,
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    yield microgrid, device

    db.query(Device).filter(Device.microgrid_id == microgrid.id).delete()
    db.query(Microgrid).filter(Microgrid.id == microgrid.id).delete()
    db.commit()
    db.close()


def test_current_energy_reading_returns_simulated_data(client, microgrid_and_device):
    microgrid, _ = microgrid_and_device
    response = client.get(f"/api/telemetry/microgrids/{microgrid.id}/current")
    assert response.status_code == 200
    body = response.json()
    assert body["microgrid_id"] == str(microgrid.id)
    assert body["source"] == "SIMULATED"
    assert body["consumption_w"] >= 0
    assert body["generation_w"] >= 0


def test_current_energy_reading_404_for_unknown_microgrid(client):
    response = client.get(f"/api/telemetry/microgrids/{uuid.uuid4()}/current")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_energy_history_returns_readings_in_range(client, microgrid_and_device):
    microgrid, _ = microgrid_and_device
    start = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 1, 0, tzinfo=timezone.utc)
    response = client.get(
        f"/api/telemetry/microgrids/{microgrid.id}/history",
        params={"start": start.isoformat(), "end": end.isoformat(), "interval_minutes": 30},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["readings"]) == 3
    assert all(r["source"] == "SIMULATED" for r in body["readings"])


def test_energy_history_rejects_invalid_range(client, microgrid_and_device):
    microgrid, _ = microgrid_and_device
    start = datetime(2026, 6, 15, 5, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 1, 0, tzinfo=timezone.utc)  # end before start
    response = client.get(
        f"/api/telemetry/microgrids/{microgrid.id}/history",
        params={"start": start.isoformat(), "end": end.isoformat(), "interval_minutes": 15},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RANGE"


def test_energy_history_repeated_call_is_idempotent(client, microgrid_and_device):
    microgrid, _ = microgrid_and_device
    start = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 16, 0, 30, tzinfo=timezone.utc)
    params = {"start": start.isoformat(), "end": end.isoformat(), "interval_minutes": 30}

    first = client.get(f"/api/telemetry/microgrids/{microgrid.id}/history", params=params).json()
    second = client.get(f"/api/telemetry/microgrids/{microgrid.id}/history", params=params).json()

    first_values = [(r["recorded_at"], r["consumption_w"], r["generation_w"]) for r in first["readings"]]
    second_values = [(r["recorded_at"], r["consumption_w"], r["generation_w"]) for r in second["readings"]]
    assert first_values == second_values


def test_current_device_reading_returns_simulated_data(client, microgrid_and_device):
    _, device = microgrid_and_device
    response = client.get(f"/api/telemetry/devices/{device.id}/current")
    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == str(device.id)
    assert body["source"] == "SIMULATED"
    assert body["voltage_v"] > 0


def test_current_device_reading_404_for_unknown_device(client):
    response = client.get(f"/api/telemetry/devices/{uuid.uuid4()}/current")
    assert response.status_code == 404


def test_device_history_returns_readings_in_range(client, microgrid_and_device):
    _, device = microgrid_and_device
    start = datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 11, 0, tzinfo=timezone.utc)
    response = client.get(
        f"/api/telemetry/devices/{device.id}/history",
        params={"start": start.isoformat(), "end": end.isoformat(), "interval_minutes": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["readings"]) == 4
