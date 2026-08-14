import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.telemetry import EnergyReading, TelemetrySource
from app.services.analytics.metrics import compute_energy_summary

MICROGRID_ID = uuid.uuid4()


def _reading(hour_offset: float, consumption_w, generation_w, grid_import_w=None, grid_export_w=None, battery_power_w=None):
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    at = base + timedelta(hours=hour_offset)
    imp = grid_import_w if grid_import_w is not None else max(0.0, consumption_w - generation_w)
    exp = grid_export_w if grid_export_w is not None else max(0.0, generation_w - consumption_w)
    return EnergyReading(
        microgrid_id=MICROGRID_ID,
        recorded_at=at,
        consumption_w=consumption_w,
        generation_w=generation_w,
        grid_import_w=imp,
        grid_export_w=exp,
        available_energy_w=generation_w,
        battery_soc_percent=50.0,
        battery_power_w=battery_power_w,
        source=TelemetrySource.SIMULATED,
    )


def test_constant_power_over_one_hour_yields_expected_energy():
    # 1000W constant for exactly 1 hour -> 1000 Wh, via trapezoidal integration.
    readings = [_reading(0, 1000.0, 0.0), _reading(1, 1000.0, 0.0)]
    summary = compute_energy_summary(readings)
    assert summary.total_consumption_wh == pytest.approx(1000.0, abs=0.01)


def test_ramp_uses_trapezoidal_integration():
    # Power ramps from 0 to 1000W over 1 hour -> average 500W -> 500 Wh.
    readings = [_reading(0, 0.0, 0.0), _reading(1, 1000.0, 0.0)]
    summary = compute_energy_summary(readings)
    assert summary.total_consumption_wh == pytest.approx(500.0, abs=0.01)


def test_solar_self_consumption_is_capped_at_the_lesser_of_generation_and_consumption():
    # Generation exceeds consumption throughout -> self-consumption == consumption.
    readings = [_reading(0, 200.0, 800.0), _reading(1, 200.0, 800.0)]
    summary = compute_energy_summary(readings)
    assert summary.solar_self_consumption_wh == pytest.approx(200.0, abs=0.01)
    assert summary.grid_export_wh == pytest.approx(600.0, abs=0.01)
    assert summary.grid_import_wh == pytest.approx(0.0, abs=0.01)


def test_peak_and_average_demand():
    readings = [_reading(0, 100.0, 0.0), _reading(1, 500.0, 0.0), _reading(2, 300.0, 0.0)]
    summary = compute_energy_summary(readings)
    assert summary.peak_demand_w == 500.0
    assert summary.average_demand_w == pytest.approx((100.0 + 500.0 + 300.0) / 3, abs=0.01)


def test_load_factor_is_ratio_of_average_to_peak():
    readings = [_reading(0, 200.0, 0.0), _reading(1, 200.0, 0.0), _reading(2, 800.0, 0.0)]
    summary = compute_energy_summary(readings)
    expected_avg = (200.0 + 200.0 + 800.0) / 3
    assert summary.load_factor == pytest.approx(expected_avg / 800.0, abs=0.001)


def test_renewable_contribution_and_grid_dependency_are_complementary_when_no_export():
    # No export means all consumption is either self-consumed solar or grid import.
    readings = [_reading(0, 500.0, 200.0), _reading(1, 500.0, 200.0)]
    summary = compute_energy_summary(readings)
    assert summary.renewable_contribution_pct + summary.grid_dependency_pct == pytest.approx(100.0, abs=0.1)


def test_battery_metrics_present_when_battery_power_provided():
    readings = [
        _reading(0, 500.0, 200.0, battery_power_w=100.0),   # discharging
        _reading(1, 500.0, 200.0, battery_power_w=-50.0),   # charging
    ]
    summary = compute_energy_summary(readings)
    assert summary.battery_discharge_wh is not None
    assert summary.battery_charge_wh is not None
    assert summary.battery_throughput_wh == pytest.approx(
        summary.battery_charge_wh + summary.battery_discharge_wh, abs=0.01
    )


def test_battery_metrics_absent_when_battery_power_missing():
    readings = [_reading(0, 500.0, 200.0, battery_power_w=None), _reading(1, 500.0, 200.0, battery_power_w=None)]
    summary = compute_energy_summary(readings)
    assert summary.battery_charge_wh is None
    assert summary.battery_discharge_wh is None
    assert summary.battery_throughput_wh is None


def test_zero_consumption_gives_none_load_factor_and_renewable_pct():
    readings = [_reading(0, 0.0, 0.0), _reading(1, 0.0, 0.0)]
    summary = compute_energy_summary(readings)
    assert summary.load_factor is None
    assert summary.renewable_contribution_pct is None
    assert summary.grid_dependency_pct is None
