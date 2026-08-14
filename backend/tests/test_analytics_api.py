import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource


@pytest.fixture()
def microgrid_with_readings():
    db = SessionLocal()
    microgrid = Microgrid(
        name=f"analytics-test-{uuid.uuid4()}",
        location="Test Site",
        status=MicrogridStatus.ACTIVE,
    )
    db.add(microgrid)
    db.commit()
    db.refresh(microgrid)

    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    rows = []
    for h in range(24):
        consumption = 900.0 if h == 19 else 200.0
        generation = max(0.0, 500.0 - abs(h - 12) * 60)
        imp = max(0.0, consumption - generation)
        exp = max(0.0, generation - consumption)
        rows.append(
            EnergyReading(
                microgrid_id=microgrid.id,
                recorded_at=base + timedelta(hours=h),
                consumption_w=consumption,
                generation_w=generation,
                grid_import_w=imp,
                grid_export_w=exp,
                available_energy_w=generation,
                battery_soc_percent=50.0,
                battery_power_w=0.0,
                source=TelemetrySource.SIMULATED,
            )
        )
    db.add_all(rows)
    db.commit()

    yield microgrid, base, base + timedelta(hours=23)

    db.query(EnergyReading).filter(EnergyReading.microgrid_id == microgrid.id).delete()
    db.query(Microgrid).filter(Microgrid.id == microgrid.id).delete()
    db.commit()
    db.close()


def test_energy_summary_endpoint(client, microgrid_with_readings):
    microgrid, start, end = microgrid_with_readings
    response = client.get(
        f"/api/energy/microgrids/{microgrid.id}/summary",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reading_count"] == 24
    assert body["peak_demand_w"] == 900.0
    assert body["total_consumption_wh"] > 0


def test_consumption_patterns_endpoint(client, microgrid_with_readings):
    microgrid, start, end = microgrid_with_readings
    response = client.get(
        f"/api/energy/microgrids/{microgrid.id}/patterns",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reading_count"] == 24
    assert any(p["hour"] == 19 for p in body["peak_periods"])


def test_energy_profile_endpoint(client, microgrid_with_readings):
    microgrid, start, end = microgrid_with_readings
    response = client.get(
        f"/api/energy/microgrids/{microgrid.id}/profile",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["peak_hour"] == 19
    assert isinstance(body["characteristics"], list)


def test_analytics_404_for_unknown_microgrid(client):
    response = client.get(f"/api/energy/microgrids/{uuid.uuid4()}/summary")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_analytics_insufficient_data_when_no_readings_exist(client):
    db = SessionLocal()
    microgrid = Microgrid(name=f"empty-{uuid.uuid4()}", location="Nowhere", status=MicrogridStatus.ACTIVE)
    db.add(microgrid)
    db.commit()
    db.refresh(microgrid)
    microgrid_id = microgrid.id
    db.close()

    response = client.get(f"/api/energy/microgrids/{microgrid_id}/summary")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"

    db = SessionLocal()
    db.query(Microgrid).filter(Microgrid.id == microgrid_id).delete()
    db.commit()
    db.close()


def test_analytics_rejects_invalid_time_range(client, microgrid_with_readings):
    microgrid, start, end = microgrid_with_readings
    response = client.get(
        f"/api/energy/microgrids/{microgrid.id}/summary",
        params={"start": end.isoformat(), "end": start.isoformat()},  # reversed
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RANGE"


def test_analytics_does_not_mix_simulated_and_hardware_sources(client, microgrid_with_readings):
    microgrid, start, end = microgrid_with_readings

    # Insert a HARDWARE-tagged reading with a very different value in the
    # same window; requesting SIMULATED explicitly must not be affected by it.
    db = SessionLocal()
    db.add(
        EnergyReading(
            microgrid_id=microgrid.id,
            recorded_at=start + timedelta(hours=5, minutes=30),
            consumption_w=99999.0,
            generation_w=0.0,
            grid_import_w=99999.0,
            grid_export_w=0.0,
            available_energy_w=0.0,
            battery_soc_percent=None,
            battery_power_w=None,
            source=TelemetrySource.HARDWARE,
        )
    )
    db.commit()
    db.close()

    response = client.get(
        f"/api/energy/microgrids/{microgrid.id}/summary",
        params={"start": start.isoformat(), "end": end.isoformat(), "source": "SIMULATED"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["peak_demand_w"] == 900.0  # unaffected by the HARDWARE outlier
    assert body["reading_count"] == 24

    db = SessionLocal()
    db.query(EnergyReading).filter(EnergyReading.source == TelemetrySource.HARDWARE).filter(
        EnergyReading.microgrid_id == microgrid.id
    ).delete()
    db.commit()
    db.close()


def test_analytics_default_lookback_when_no_range_given(client, microgrid_with_readings):
    # No start/end -> defaults to the last N days ending "now"; readings from
    # 2026-06-15 will be outside that window relative to the real current
    # date, so this should legitimately report insufficient data rather than
    # silently returning unrelated results.
    microgrid, _, _ = microgrid_with_readings
    response = client.get(f"/api/energy/microgrids/{microgrid.id}/summary")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"
