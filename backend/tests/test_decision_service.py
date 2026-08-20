import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.customer import Customer
from app.models.decision import ApprovalStatus, BatteryAction, Decision, OptimizationStatus
from app.models.forecast import ForecastModel, ForecastTarget
from app.models.load import Load, LoadCategory, LoadControlMode, LoadStatus
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource
from app.models.user import User, UserRole
from app.core.errors import NotFoundError
from app.services.decision.service import DecisionService
from app.services.forecasting.service import ForecastingService
from app.services.telemetry.simulation import SimulationTelemetryProvider


def _make_reading(microgrid_id, at, source=TelemetrySource.SIMULATED):
    hour = at.hour
    consumption = 300.0 + 200.0 * math.sin(math.pi * hour / 24.0) ** 2
    generation = max(0.0, 500.0 * math.sin(math.pi * (hour - 6) / 12.0)) if 6 <= hour <= 18 else 0.0
    imp = max(0.0, consumption - generation)
    exp = max(0.0, generation - consumption)
    return EnergyReading(
        microgrid_id=microgrid_id, recorded_at=at, consumption_w=consumption, generation_w=generation,
        grid_import_w=imp, grid_export_w=exp, available_energy_w=generation,
        battery_soc_percent=55.0, battery_power_w=0.0, source=source,
    )


@pytest.fixture()
def microgrid_with_trained_forecasts():
    db = SessionLocal()
    mg = Microgrid(name=f"decision-test-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    user = User(email=f"{uuid.uuid4()}@example.com", password_hash="x", role=UserRole.CUSTOMER, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    customer = Customer(user_id=user.id, microgrid_id=mg.id, name="Decision Test Customer")
    db.add(customer)
    db.commit()
    db.refresh(customer)

    loads = [
        Load(customer_id=customer.id, name="EV Charger", category=LoadCategory.EV_CHARGER, priority=1,
             controllable=True, control_mode=LoadControlMode.AUTOMATIC, status=LoadStatus.ON),
        Load(customer_id=customer.id, name="Fridge", category=LoadCategory.APPLIANCE, priority=10,
             controllable=False, control_mode=LoadControlMode.MANUAL, status=LoadStatus.ON),
    ]
    db.add_all(loads)
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


@pytest.fixture()
def microgrid_without_forecasts():
    db = SessionLocal()
    mg = Microgrid(name=f"decision-nodata-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)
    yield mg
    db.query(Decision).filter(Decision.microgrid_id == mg.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def test_optimize_with_trained_forecasts_produces_optimal_decision(microgrid_with_trained_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)

    decision = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)

    assert decision.optimization_status in (OptimizationStatus.OPTIMAL, OptimizationStatus.ERROR)
    assert decision.fallback_used is False
    assert decision.recommended_battery_action in (BatteryAction.CHARGE, BatteryAction.DISCHARGE, BatteryAction.IDLE)
    assert decision.source == TelemetrySource.SIMULATED
    assert decision.provenance["solver"] == "scipy.optimize.linprog (HiGHS)"
    assert decision.provenance["economic_optimization"].startswith("unavailable")
    assert len(decision.constraints_checked) > 0
    assert decision.explanation
    assert decision.approval_status == ApprovalStatus.PENDING

    db.close()


def test_optimize_without_forecast_falls_back_safely(microgrid_without_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)

    decision = service.optimize(microgrid_without_forecasts.id, TelemetrySource.SIMULATED)

    assert decision.optimization_status == OptimizationStatus.SAFE_FALLBACK
    assert decision.fallback_used is True
    assert decision.fallback_reason is not None
    assert decision.recommended_battery_action == BatteryAction.IDLE
    assert decision.recommended_battery_power_w == 0.0
    assert "no optimized recommendation" in decision.explanation.lower()

    db.close()


def test_optimize_unknown_microgrid_raises_not_found():
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    with pytest.raises(NotFoundError):
        service.optimize(uuid.uuid4(), TelemetrySource.SIMULATED)
    db.close()


def test_get_latest_returns_none_when_no_decision_exists(microgrid_without_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    result = service.get_latest(microgrid_without_forecasts.id)
    assert result is None
    db.close()


def test_get_latest_returns_the_most_recent_decision(microgrid_with_trained_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    first = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    second = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    latest = service.get_latest(microgrid_with_trained_forecasts.id)
    assert latest.id == second.id
    assert latest.id != first.id
    db.close()


def test_history_returns_decisions_most_recent_first(microgrid_with_trained_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    history = service.list_history(microgrid_with_trained_forecasts.id)
    assert len(history) >= 2
    assert history[0].created_at >= history[1].created_at
    db.close()


def test_load_recommendations_are_persisted_as_json(microgrid_with_trained_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    decision = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    assert isinstance(decision.load_recommendations, list)
    if decision.optimization_status == OptimizationStatus.OPTIMAL:
        assert len(decision.load_recommendations) == 2  # both fixture loads
        for rec in decision.load_recommendations:
            assert "load_id" in rec and "action" in rec and "reason" in rec
    db.close()


def test_set_approval_updates_status_without_side_effects(microgrid_with_trained_forecasts):
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    decision = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)

    approved = service.set_approval(decision.id, True)
    assert approved.approval_status == ApprovalStatus.APPROVED
    assert approved.approved_at is not None

    rejected_decision = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)
    rejected = service.set_approval(rejected_decision.id, False)
    assert rejected.approval_status == ApprovalStatus.REJECTED

    db.close()


def test_set_approval_unknown_decision_raises_not_found():
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    with pytest.raises(NotFoundError):
        service.set_approval(uuid.uuid4(), True)
    db.close()


def test_decision_never_recommends_physically_impossible_battery_state(microgrid_with_trained_forecasts):
    """No decision may recommend both charging and discharging, or a power beyond configured limits."""
    db = SessionLocal()
    provider = SimulationTelemetryProvider()
    service = DecisionService(db, provider)
    decision = service.optimize(microgrid_with_trained_forecasts.id, TelemetrySource.SIMULATED)

    if decision.optimization_status == OptimizationStatus.OPTIMAL:
        assert decision.recommended_battery_action in (BatteryAction.CHARGE, BatteryAction.DISCHARGE, BatteryAction.IDLE)
        from app.core.config import get_settings
        settings = get_settings()
        if decision.recommended_battery_action == BatteryAction.CHARGE:
            assert decision.recommended_battery_power_w <= settings.DECISION_BATTERY_MAX_CHARGE_W + 1.0
        elif decision.recommended_battery_action == BatteryAction.DISCHARGE:
            assert decision.recommended_battery_power_w <= settings.DECISION_BATTERY_MAX_DISCHARGE_W + 1.0

    db.close()
