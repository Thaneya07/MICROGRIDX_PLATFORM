import uuid

import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.device import Device, DeviceStatus, DeviceType
from app.models.load import Load, LoadCategory, LoadControlMode, LoadStatus
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.user import User, UserRole


@pytest.fixture()
def full_microgrid():
    """A microgrid with a solar inverter, battery, meter, load controller, sensor, and one load."""
    db = SessionLocal()
    mg = Microgrid(name=f"scene-test-{uuid.uuid4()}", location="Test Site", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="x", role=UserRole.CUSTOMER, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    customer = Customer(user_id=user.id, microgrid_id=mg.id, name="Test Customer")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    devices = [
        Device(microgrid_id=mg.id, device_type=DeviceType.SOLAR_INVERTER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=mg.id, device_type=DeviceType.BATTERY, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=mg.id, device_type=DeviceType.METER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=mg.id, device_type=DeviceType.LOAD_CONTROLLER, status=DeviceStatus.OFFLINE),
        Device(microgrid_id=mg.id, device_type=DeviceType.SENSOR, status=DeviceStatus.OFFLINE),
    ]
    db.add_all(devices)
    db.commit()

    load = Load(
        customer_id=customer.id,
        name="Water Pump",
        category=LoadCategory.OTHER,
        priority=2,
        controllable=True,
        control_mode=LoadControlMode.AUTOMATIC,
        status=LoadStatus.ON,
    )
    db.add(load)
    db.commit()

    yield mg

    db.query(Load).filter(Load.customer_id == customer.id).delete()
    db.query(Device).filter(Device.microgrid_id == mg.id).delete()
    db.query(Customer).filter(Customer.id == customer.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def test_snapshot_rest_endpoint_returns_full_scene_data(client, full_microgrid):
    response = client.get(f"/api/telemetry/microgrids/{full_microgrid.id}/snapshot")
    assert response.status_code == 200
    body = response.json()

    assert body["microgrid_id"] == str(full_microgrid.id)
    assert body["source"] == "SIMULATED"
    assert body["energy_reading"] is not None
    assert body["energy_reading"]["source"] == "SIMULATED"

    device_types = {d["device_type"] for d in body["devices"]}
    assert device_types == {"SOLAR_INVERTER", "BATTERY", "METER", "LOAD_CONTROLLER", "SENSOR"}
    assert all(d["source"] == "SIMULATED" for d in body["devices"])

    assert len(body["loads"]) == 1
    assert body["loads"][0]["name"] == "Water Pump"
    assert body["loads"][0]["status"] == "ON"


def test_snapshot_rest_endpoint_404_for_unknown_microgrid(client):
    response = client.get(f"/api/telemetry/microgrids/{uuid.uuid4()}/snapshot")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_snapshot_battery_reading_has_signed_context_via_energy_reading(client, full_microgrid):
    # battery_power_w on the microgrid-level energy_reading is the signed
    # charge/discharge indicator used by the 3D scene; device-level power
    # is unsigned magnitude (see telemetry consistency review notes).
    response = client.get(f"/api/telemetry/microgrids/{full_microgrid.id}/snapshot")
    body = response.json()
    assert "battery_power_w" in body["energy_reading"]
    assert "battery_soc_percent" in body["energy_reading"]


def test_websocket_stream_sends_snapshot_and_can_be_closed(client, full_microgrid):
    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws:
        message = ws.receive_json()
        assert message["type"] == "snapshot"
        assert message["microgrid_id"] == str(full_microgrid.id)
        assert message["source"] == "SIMULATED"
        assert message["energy_reading"] is not None
        assert len(message["devices"]) == 5

        # A second tick should also be a valid snapshot (stream keeps running).
        second = ws.receive_json()
        assert second["type"] == "snapshot"


def test_websocket_stream_closes_for_unknown_microgrid(client):
    unknown_id = uuid.uuid4()
    with client.websocket_connect(f"/api/telemetry/microgrids/{unknown_id}/stream?interval_seconds=1") as ws:
        message = ws.receive_json()
        assert message["type"] == "error"
        assert message["code"] == "NOT_FOUND"


def test_websocket_stream_payload_matches_rest_snapshot_shape(client, full_microgrid):
    rest_response = client.get(f"/api/telemetry/microgrids/{full_microgrid.id}/snapshot")
    rest_body = rest_response.json()

    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws:
        ws_message = ws.receive_json()

    rest_keys = set(rest_body.keys())
    ws_keys = set(ws_message.keys()) - {"type"}
    assert rest_keys == ws_keys


def test_websocket_stream_device_snapshots_include_device_type_for_scene_routing(client, full_microgrid):
    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws:
        message = ws.receive_json()
    for device in message["devices"]:
        assert "device_type" in device
        assert "status" in device
        assert "power_w" in device
        assert device["power_w"] >= 0


def test_websocket_stream_periodic_updates_use_configured_interval(client, full_microgrid):
    """Confirms the stream ticks repeatedly (not just once) using the requested interval."""
    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws:
        first = ws.receive_json()
        second = ws.receive_json()
        third = ws.receive_json()
        for msg in (first, second, third):
            assert msg["type"] == "snapshot"
            assert msg["source"] == "SIMULATED"


def test_websocket_stream_disconnect_is_graceful_and_does_not_affect_new_connections(client, full_microgrid):
    """Closing a stream client should not leave the server in a bad state for subsequent connections."""
    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws:
        ws.receive_json()
    # Context manager exit closes the socket (graceful disconnect). A fresh
    # connection to the same microgrid must still work normally afterward.
    with client.websocket_connect(
        f"/api/telemetry/microgrids/{full_microgrid.id}/stream?interval_seconds=1"
    ) as ws2:
        message = ws2.receive_json()
        assert message["type"] == "snapshot"


def test_rest_snapshot_invalid_id_format_returns_422(client):
    """A malformed (non-UUID) microgrid id should fail request validation, not 500."""
    response = client.get("/api/telemetry/microgrids/not-a-valid-uuid/snapshot")
    assert response.status_code == 422


def test_snapshot_source_propagates_consistently_across_energy_and_device_readings(client, full_microgrid):
    response = client.get(f"/api/telemetry/microgrids/{full_microgrid.id}/snapshot")
    body = response.json()
    assert body["source"] == "SIMULATED"
    assert body["energy_reading"]["source"] == "SIMULATED"
    assert all(d["source"] == "SIMULATED" for d in body["devices"])
