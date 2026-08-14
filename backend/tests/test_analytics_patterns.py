import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.telemetry import EnergyReading, TelemetrySource
from app.services.analytics.patterns import (
    analyze_consumption_patterns,
    compute_base_load_w,
    compute_consumption_variability,
    compute_peak_periods,
    compute_solar_load_correlation,
    compute_weekday_weekend_averages,
    compute_hourly_patterns,
)

MICROGRID_ID = uuid.uuid4()


def _reading(dt: datetime, consumption_w, generation_w=0.0, battery_power_w=None):
    return EnergyReading(
        microgrid_id=MICROGRID_ID,
        recorded_at=dt,
        consumption_w=consumption_w,
        generation_w=generation_w,
        grid_import_w=max(0.0, consumption_w - generation_w),
        grid_export_w=max(0.0, generation_w - consumption_w),
        available_energy_w=generation_w,
        battery_soc_percent=50.0,
        battery_power_w=battery_power_w,
        source=TelemetrySource.SIMULATED,
    )


def test_hourly_patterns_group_correctly_by_hour_of_day():
    base = datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc)  # Monday
    readings = [
        _reading(base, 100.0),
        _reading(base + timedelta(days=1), 300.0),  # same hour, next day
        _reading(base.replace(hour=20), 50.0),
    ]
    patterns = compute_hourly_patterns(readings)
    hour_8 = next(p for p in patterns if p.hour == 8)
    assert hour_8.average_consumption_w == pytest.approx(200.0, abs=0.01)
    assert hour_8.sample_count == 2


def test_peak_periods_empty_for_flat_profile():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 200.0) for h in range(24)]
    patterns = compute_hourly_patterns(readings)
    peaks = compute_peak_periods(patterns)
    assert peaks == []  # perfectly flat load has no meaningful peak


def test_peak_periods_detects_clear_peak_hour():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = []
    for h in range(24):
        consumption = 900.0 if h == 19 else 100.0
        readings.append(_reading(base + timedelta(hours=h), consumption))
    patterns = compute_hourly_patterns(readings)
    peaks = compute_peak_periods(patterns)
    assert peaks[0].hour == 19


def test_base_load_is_low_percentile_not_minimum():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    # One low outlier reading should not single-handedly set the base load.
    values = [100.0] * 9 + [10.0]
    readings = [_reading(base + timedelta(hours=i), v) for i, v in enumerate(values)]
    base_load = compute_base_load_w(readings)
    assert base_load < 100.0  # pulled down by the low reading
    assert base_load > 10.0  # but not equal to the single minimum outlier


def test_consumption_variability_zero_for_constant_load():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base + timedelta(hours=h), 250.0) for h in range(5)]
    assert compute_consumption_variability(readings) == 0.0


def test_consumption_variability_positive_for_varying_load():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    values = [100.0, 500.0, 100.0, 500.0, 100.0]
    readings = [_reading(base + timedelta(hours=i), v) for i, v in enumerate(values)]
    assert compute_consumption_variability(readings) > 0.0


def test_solar_load_correlation_none_with_insufficient_or_constant_data():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [_reading(base, 100.0, 50.0), _reading(base + timedelta(hours=1), 100.0, 50.0)]
    assert compute_solar_load_correlation(readings) is None  # constant series, zero variance


def test_solar_load_correlation_detects_positive_relationship():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    # Consumption tracks generation closely (e.g. daytime appliance use follows solar).
    readings = [
        _reading(base + timedelta(hours=i), consumption_w=g, generation_w=g)
        for i, g in enumerate([0, 100, 400, 800, 400, 100, 0])
    ]
    corr = compute_solar_load_correlation(readings)
    assert corr == pytest.approx(1.0, abs=0.01)


def test_weekday_weekend_split():
    monday = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)  # Monday
    saturday = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)  # Saturday
    readings = [_reading(monday, 300.0), _reading(saturday, 100.0)]
    weekday_avg, weekend_avg = compute_weekday_weekend_averages(readings)
    assert weekday_avg == 300.0
    assert weekend_avg == 100.0


def test_analyze_consumption_patterns_end_to_end_smoke():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    readings = [
        _reading(base + timedelta(hours=h), consumption_w=100.0 + 50 * (h % 5), generation_w=max(0, 200 - abs(h - 12) * 20))
        for h in range(48)
    ]
    result = analyze_consumption_patterns(readings)
    assert result.reading_count == 48
    assert len(result.hourly_patterns) > 0
    assert result.base_load_w >= 0
    assert result.consumption_variability >= 0
