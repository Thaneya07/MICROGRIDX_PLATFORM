import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.decision import Decision
from app.models.forecast import ForecastModel, ForecastTarget
from app.models.load import Load, LoadCategory, LoadControlMode, LoadStatus
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource
from app.models.user import User, UserRole
from app.services.forecasting.service import ForecastingService


def _make_reading(microgrid_id, at):
    hour = at.hour
    consumption = 300.0 + 200.0 * math.sin(math.pi * hour / 24.0) ** 2
    generation = max(0.0, 500.0 * math.sin(math.pi * (hour - 6) / 12.0)) if 6 <= hour <= 18 else 0.0
    imp = max(0.0, consumption - generation)
    exp = max(0.0, generation - consumption)
    return EnergyReading(
        microgrid_id=microgrid_id, recorded_at=at, consumption_w=consumption, generation_w=generation,
        grid_import_w=imp, grid_export_w=exp, available_energy_w=generation,
        battery_soc_percent=55.0, battery_power_w=0.0, source=TelemetrySource.SIMULATED,
    )


@pytest.fixture()
def microgrid_ready_for_decisions():
    db = SessionLocal()
    mg = Microgrid(name=f"decision-api-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="x", role=UserRole.CUSTOMER, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    customer = Customer(user_id=user.id, microgrid_id=mg.id, name="API Test Customer")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    load = Load(customer_id=customer.id, name="Dishwasher", category=LoadCategory.APPLIANCE, priority=2,
                controllable=True, control_mode=LoadControlMode.AUTOMATIC, status=LoadStatus.ON)
    db.add(load)
    db.commit()

    base = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = [_make_reading(mg.id, base + timedelta(hours=h)) for h in range(240)]
    db.add_all(rows)
    db.commit()

    forecasting = ForecastingService(db)
    forecasting.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    forecasting.train(mg.id, ForecastTarget.SOLAR_GENERATION, TelemetrySource.SIMULATED)

    yield mg

    db.query(Decision).filter(Decision.microgrid_id == mg.id).delete()
    db.query(ForecastModel).filter(ForecastModel.microgrid_id == mg.id).delete()
    db.query(Load).filter(Load.customer_id == customer.id).delete()
    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Customer).filter(Customer.id == customer.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def test_optimize_endpoint_returns_full_decision_contract(client, microgrid_ready_for_decisions):
    response = client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "SIMULATED"
    assert body["optimization_status"] in ("OPTIMAL", "ERROR")
    assert body["recommended_battery_action"] in ("CHARGE", "DISCHARGE", "IDLE")
    assert "safety_note" in body
    assert "does not automatically actuate" in body["safety_note"]
    assert isinstance(body["load_recommendations"], list)
    assert isinstance(body["constraints_checked"], list)
    assert body["explanation"]


def test_optimize_endpoint_404_for_unknown_microgrid(client):
    response = client.post(f"/api/decision/microgrids/{uuid.uuid4()}/optimize")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_latest_endpoint_404_before_any_optimization(client):
    db = SessionLocal()
    mg = Microgrid(name=f"no-decision-{uuid.uuid4()}", location="X", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)
    mg_id = mg.id
    db.close()

    response = client.get(f"/api/decision/microgrids/{mg_id}/latest")
    assert response.status_code == 404

    db = SessionLocal()
    db.query(Microgrid).filter(Microgrid.id == mg_id).delete()
    db.commit()
    db.close()


def test_latest_endpoint_returns_most_recent_after_optimizing(client, microgrid_ready_for_decisions):
    client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    response = client.get(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/latest")
    assert response.status_code == 200
    assert response.json()["microgrid_id"] == str(microgrid_ready_for_decisions.id)


def test_history_endpoint_returns_multiple_decisions(client, microgrid_ready_for_decisions):
    client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    response = client.get(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2


def test_approve_endpoint_records_approval(client, microgrid_ready_for_decisions):
    optimize_response = client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    decision_id = optimize_response.json()["id"]

    response = client.post(f"/api/decision/{decision_id}/approve", json={"approved": True})
    assert response.status_code == 200
    assert response.json()["approval_status"] == "APPROVED"


def test_approve_endpoint_records_rejection(client, microgrid_ready_for_decisions):
    optimize_response = client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    decision_id = optimize_response.json()["id"]

    response = client.post(f"/api/decision/{decision_id}/approve", json={"approved": False})
    assert response.status_code == 200
    assert response.json()["approval_status"] == "REJECTED"


def test_approve_endpoint_404_for_unknown_decision(client):
    response = client.post(f"/api/decision/{uuid.uuid4()}/approve", json={"approved": True})
    assert response.status_code == 404


def test_optimize_falls_back_safely_for_microgrid_without_forecast(client):
    db = SessionLocal()
    mg = Microgrid(name=f"fallback-{uuid.uuid4()}", location="X", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)
    mg_id = mg.id
    db.close()

    response = client.post(f"/api/decision/microgrids/{mg_id}/optimize")
    assert response.status_code == 200
    body = response.json()
    assert body["optimization_status"] == "SAFE_FALLBACK"
    assert body["fallback_used"] is True
    assert body["recommended_battery_action"] == "IDLE"

    db = SessionLocal()
    db.query(Decision).filter(Decision.microgrid_id == mg_id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg_id).delete()
    db.commit()
    db.close()


def test_decision_never_exposes_fabricated_economic_savings(client, microgrid_ready_for_decisions):
    """No tariff data exists in this project; the API must never claim monetary savings."""
    response = client.post(f"/api/decision/microgrids/{microgrid_ready_for_decisions.id}/optimize")
    body = response.json()
    body_str = str(body).lower()
    assert "saved $" not in body_str
    assert "cost_savings" not in body
    assert body["provenance"]["economic_optimization"].startswith("unavailable")
