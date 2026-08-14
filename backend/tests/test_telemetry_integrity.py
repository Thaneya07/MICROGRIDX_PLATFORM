import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.connection import SessionLocal
from app.models.microgrid import Microgrid, MicrogridStatus
from app.models.telemetry import EnergyReading, TelemetrySource


@pytest.fixture()
def microgrid():
    db = SessionLocal()
    mg = Microgrid(name=f"constraint-test-{uuid.uuid4()}", location="Test", status=MicrogridStatus.ACTIVE)
    db.add(mg)
    db.commit()
    db.refresh(mg)
    yield mg
    db.rollback()
    db.query(EnergyReading).filter(EnergyReading.microgrid_id == mg.id).delete()
    db.query(Microgrid).filter(Microgrid.id == mg.id).delete()
    db.commit()
    db.close()


def _reading(microgrid_id, **overrides):
    defaults = dict(
        microgrid_id=microgrid_id,
        recorded_at=datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc),
        consumption_w=100.0,
        generation_w=50.0,
        grid_import_w=50.0,
        grid_export_w=0.0,
        available_energy_w=50.0,
        battery_soc_percent=50.0,
        battery_power_w=0.0,
        source=TelemetrySource.SIMULATED,
    )
    defaults.update(overrides)
    return EnergyReading(**defaults)


def test_negative_consumption_is_rejected_by_db(microgrid):
    db = SessionLocal()
    db.add(_reading(microgrid.id, consumption_w=-10.0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_out_of_range_battery_soc_is_rejected_by_db(microgrid):
    db = SessionLocal()
    db.add(_reading(microgrid.id, battery_soc_percent=150.0))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_duplicate_timestamp_same_source_is_rejected_by_db(microgrid):
    db = SessionLocal()
    db.add(_reading(microgrid.id))
    db.commit()

    db.add(_reading(microgrid.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_same_timestamp_different_source_is_allowed(microgrid):
    db = SessionLocal()
    db.add(_reading(microgrid.id, source=TelemetrySource.SIMULATED))
    db.commit()
    db.add(_reading(microgrid.id, source=TelemetrySource.HARDWARE))
    db.commit()  # should not raise
    count = db.query(EnergyReading).filter(EnergyReading.microgrid_id == microgrid.id).count()
    assert count == 2
    db.close()
