import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.forecast import ForecastModel
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource


def _make_reading(microgrid_id, at):
    hour = at.hour
    consumption = 300.0 + 200.0 * math.sin(math.pi * hour / 24.0) ** 2
    generation = max(0.0, 500.0 * math.sin(math.pi * (hour - 6) / 12.0)) if 6 <= hour <= 18 else 0.0
    imp = max(0.0, consumption - generation)
    exp = max(0.0, generation - consumption)
    return EnergyReading(
        microgrid_id=microgrid_id,
        recorded_at=at,
        consumption_w=consumption,
        generation_w=generation,
        grid_import_w=imp,
        grid_export_w=exp,
        available_energy_w=generation,
        battery_soc_percent=50.0,
        battery_power_w=0.0,
        source=TelemetrySource.SIMULATED,
    )


@pytest.fixture()
def microgrid_with_history():
    db = SessionLocal()
    mg = Microgrid(name=f"forecast-api-test-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    base = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = [_make_reading(mg.id, base + timedelta(hours=h)) for h in range(200)]
    db.add_all(rows)
    db.commit()

    yield mg

    db.query(ForecastModel).filter(ForecastModel.microgrid_id == mg.id).delete()
    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def test_predict_before_training_returns_404(client, microgrid_with_history):
    response = client.get(
        f"/api/forecast/microgrids/{microgrid_with_history.id}",
        params={
            "target": "DEMAND",
            "start": "2026-06-01T00:00:00Z",
            "end": "2026-06-01T12:00:00Z",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_train_endpoint_returns_real_metrics(client, microgrid_with_history):
    response = client.post(
        f"/api/forecast/microgrids/{microgrid_with_history.id}/train",
        params={"target": "DEMAND"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["algorithm"] == "RandomForestRegressor"
    assert body["dataset_source"] == "SIMULATED"
    assert body["status"] == "TRAINED"
    assert "test" in body["metrics"]
    assert "baseline_test" in body["metrics"]
    assert "SIMULATED" in body["data_provenance_note"]


def test_train_with_insufficient_data_returns_422(client):
    db = SessionLocal()
    mg = Microgrid(name=f"empty-forecast-{uuid.uuid4()}", location="Nowhere", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)
    mg_id = mg.id
    db.close()

    response = client.post(f"/api/forecast/microgrids/{mg_id}/train", params={"target": "DEMAND"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"

    db = SessionLocal()
    db.query(Microgrid).filter(Microgrid.id == mg_id).delete()
    db.commit()
    db.close()


def test_predict_after_training_returns_forecast_points(client, microgrid_with_history):
    train_response = client.post(
        f"/api/forecast/microgrids/{microgrid_with_history.id}/train",
        params={"target": "SOLAR_GENERATION"},
    )
    assert train_response.status_code == 200

    response = client.get(
        f"/api/forecast/microgrids/{microgrid_with_history.id}",
        params={
            "target": "SOLAR_GENERATION",
            "start": "2026-06-01T00:00:00Z",
            "end": "2026-06-01T06:00:00Z",
            "interval_minutes": 60,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 7
    assert body["target"] == "SOLAR_GENERATION"
    assert "FORECAST" in body["data_provenance_note"]
    for point in body["points"]:
        assert point["predicted_w"] >= 0
        assert point["lower_95_w"] <= point["predicted_w"] <= point["upper_95_w"]


def test_forecast_horizon_too_long_returns_400(client, microgrid_with_history):
    client.post(f"/api/forecast/microgrids/{microgrid_with_history.id}/train", params={"target": "DEMAND"})
    response = client.get(
        f"/api/forecast/microgrids/{microgrid_with_history.id}",
        params={
            "target": "DEMAND",
            "start": "2026-06-01T00:00:00Z",
            "end": "2026-08-01T00:00:00Z",  # far beyond FORECAST_MAX_HORIZON_DAYS
            "interval_minutes": 60,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_HORIZON"


def test_list_models_endpoint(client, microgrid_with_history):
    client.post(f"/api/forecast/microgrids/{microgrid_with_history.id}/train", params={"target": "DEMAND"})
    response = client.get(f"/api/forecast/microgrids/{microgrid_with_history.id}/models")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["target"] == "DEMAND"


def test_analytics_404_for_unknown_microgrid_train(client):
    response = client.post(f"/api/forecast/microgrids/{uuid.uuid4()}/train", params={"target": "DEMAND"})
    assert response.status_code == 404
