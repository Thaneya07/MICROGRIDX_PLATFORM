import math
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.database.connection import SessionLocal
from app.models.forecast import ForecastModel, ForecastModelStatus, ForecastTarget
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource
from app.core.errors import InsufficientDataError, NotFoundError
from app.services.forecasting.service import ForecastingService, InvalidHorizonError


def _make_reading(microgrid_id, at, source=TelemetrySource.SIMULATED):
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
        source=source,
    )


@pytest.fixture()
def microgrid_with_rich_history():
    db = SessionLocal()
    mg = Microgrid(name=f"forecast-test-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    base = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = [_make_reading(mg.id, base + timedelta(hours=h)) for h in range(240)]
    db.add_all(rows)
    db.commit()

    yield mg, base, base + timedelta(hours=239)

    db.query(ForecastModel).filter(ForecastModel.microgrid_id == mg.id).delete()
    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


@pytest.fixture()
def microgrid_with_sparse_history():
    db = SessionLocal()
    mg = Microgrid(name=f"forecast-sparse-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)

    base = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    rows = [_make_reading(mg.id, base + timedelta(hours=h)) for h in range(5)]
    db.add_all(rows)
    db.commit()

    yield mg

    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def test_train_raises_insufficient_data_for_sparse_history(microgrid_with_sparse_history):
    db = SessionLocal()
    service = ForecastingService(db)
    with pytest.raises(InsufficientDataError):
        service.train(microgrid_with_sparse_history.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    db.close()


def test_train_raises_not_found_for_unknown_microgrid():
    db = SessionLocal()
    service = ForecastingService(db)
    with pytest.raises(NotFoundError):
        service.train(uuid.uuid4(), ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    db.close()


def test_train_succeeds_and_persists_model_with_real_metrics(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()
    service = ForecastingService(db)

    model_row = service.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)

    assert model_row.status == ForecastModelStatus.TRAINED
    assert model_row.algorithm == "RandomForestRegressor"
    assert model_row.n_train + model_row.n_validation + model_row.n_test == 240
    assert "test" in model_row.metrics
    assert "baseline_test" in model_row.metrics
    assert model_row.metrics["test"]["mae"] >= 0
    assert model_row.metrics["test"]["n"] == model_row.n_test
    import os
    assert os.path.exists(model_row.model_path)

    db.close()


def test_predict_without_trained_model_raises_not_found(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()
    service = ForecastingService(db)
    with pytest.raises(NotFoundError):
        service.predict(
            mg.id, ForecastTarget.SOLAR_GENERATION, TelemetrySource.SIMULATED,
            start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            end=datetime(2026, 6, 2, tzinfo=timezone.utc),
            interval_minutes=60,
        )
    db.close()


def test_predict_after_training_returns_reasonable_points(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()
    service = ForecastingService(db)
    service.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)

    points = service.predict(
        mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED,
        start=datetime(2026, 6, 1, tzinfo=timezone.utc),
        end=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        interval_minutes=60,
    )
    assert len(points) == 13
    for p in points:
        assert p.prediction.mean >= 0
        assert p.prediction.lower_95 <= p.prediction.mean <= p.prediction.upper_95
    db.close()


def test_predict_rejects_invalid_horizon(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()
    service = ForecastingService(db)
    service.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    with pytest.raises(InvalidHorizonError):
        service.predict(
            mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED,
            start=datetime(2026, 6, 2, tzinfo=timezone.utc),
            end=datetime(2026, 6, 1, tzinfo=timezone.utc),
            interval_minutes=60,
        )
    db.close()


def test_training_only_uses_requested_source(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()

    hw_rows = [
        _make_reading(mg.id, start + timedelta(hours=h), source=TelemetrySource.HARDWARE)
        for h in range(100)
    ]
    for r in hw_rows:
        r.consumption_w = 99999.0
        r.grid_import_w = 99999.0
    db.add_all(hw_rows)
    db.commit()

    service = ForecastingService(db)
    model_row = service.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    assert model_row.n_train + model_row.n_validation + model_row.n_test == 240

    db.query(EnergyReading).filter(EnergyReading.source == TelemetrySource.HARDWARE).filter(
        EnergyReading.microgrid_id == mg.id
    ).delete()
    db.commit()
    db.close()


def test_list_models_returns_trained_models_most_recent_first(microgrid_with_rich_history):
    mg, start, end = microgrid_with_rich_history
    db = SessionLocal()
    service = ForecastingService(db)
    service.train(mg.id, ForecastTarget.DEMAND, TelemetrySource.SIMULATED)
    service.train(mg.id, ForecastTarget.SOLAR_GENERATION, TelemetrySource.SIMULATED)

    all_models = service.list_models(mg.id, target=None)
    assert len(all_models) == 2

    demand_only = service.list_models(mg.id, target=ForecastTarget.DEMAND)
    assert len(demand_only) == 1
    assert demand_only[0].target == ForecastTarget.DEMAND
    db.close()
