import uuid
from datetime import datetime, timedelta, timezone

from app.models.telemetry import EnergyReading, TelemetrySource
from app.services.analytics.profile import build_customer_energy_profile

MICROGRID_ID = uuid.uuid4()


def _reading(dt: datetime, consumption_w, generation_w=0.0):
    return EnergyReading(
        microgrid_id=MICROGRID_ID,
        recorded_at=dt,
        consumption_w=consumption_w,
        generation_w=generation_w,
        grid_import_w=max(0.0, consumption_w - generation_w),
        grid_export_w=max(0.0, generation_w - consumption_w),
        available_energy_w=generation_w,
        battery_soc_percent=50.0,
        battery_power_w=None,
        source=TelemetrySource.SIMULATED,
    )


def test_profile_labels_evening_heavy_when_data_supports_it():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = []
    for day in range(3):
        for h in range(24):
            if 17 <= h <= 21:
                c = 900.0
            elif 6 <= h <= 9:
                c = 200.0
            else:
                c = 150.0
            readings.append(_reading(base + timedelta(days=day, hours=h), c))
    profile = build_customer_energy_profile(readings)
    labels = {c.label for c in profile.characteristics}
    assert "evening-heavy" in labels
    for c in profile.characteristics:
        assert c.basis and any(ch.isdigit() for ch in c.basis)


def test_profile_labels_morning_heavy_when_data_supports_it():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = []
    for day in range(3):
        for h in range(24):
            if 6 <= h <= 9:
                c = 900.0
            elif 17 <= h <= 21:
                c = 200.0
            else:
                c = 150.0
            readings.append(_reading(base + timedelta(days=day, hours=h), c))
    profile = build_customer_energy_profile(readings)
    labels = {c.label for c in profile.characteristics}
    assert "morning-heavy" in labels


def test_profile_does_not_label_period_dominance_for_balanced_load():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 300.0) for h in range(24)]
    profile = build_customer_energy_profile(readings)
    labels = {c.label for c in profile.characteristics}
    assert "evening-heavy" not in labels
    assert "morning-heavy" not in labels


def test_profile_solar_dominant_label_requires_high_self_consumption():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 100.0, 500.0) for h in range(10)]
    profile = build_customer_energy_profile(readings)
    labels = {c.label for c in profile.characteristics}
    assert "solar-dominant" in labels
    assert profile.solar_utilization_pct == 100.0


def test_profile_grid_dependent_label_requires_high_grid_share():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 300.0, 0.0) for h in range(10)]
    profile = build_customer_energy_profile(readings)
    labels = {c.label for c in profile.characteristics}
    assert "grid-dependent" in labels
    assert profile.grid_dependency_pct == 100.0


def test_profile_peak_hour_matches_detected_peak_period():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 900.0 if h == 19 else 100.0) for h in range(24)]
    profile = build_customer_energy_profile(readings)
    assert profile.peak_hour == 19
