import uuid
from datetime import datetime, timezone

import pytest

from app.models.device import DeviceStatus, DeviceType
from app.models.telemetry import TelemetrySource
from app.services.telemetry.simulation import SimulationTelemetryProvider

MICROGRID_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEVICE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_energy_reading_is_deterministic_for_same_minute():
    provider = SimulationTelemetryProvider()
    at = datetime(2026, 6, 15, 12, 30, tzinfo=timezone.utc)
    first = provider._energy_reading_at(MICROGRID_ID, at)
    second = provider._energy_reading_at(MICROGRID_ID, at)
    assert first == second


def test_solar_generation_is_zero_at_night():
    provider = SimulationTelemetryProvider()
    midnight = datetime(2026, 6, 15, 2, 0, tzinfo=timezone.utc)
    reading = provider._energy_reading_at(MICROGRID_ID, midnight)
    assert reading.generation_w == 0.0


def test_solar_generation_is_positive_at_midday():
    provider = SimulationTelemetryProvider()
    noon = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    reading = provider._energy_reading_at(MICROGRID_ID, noon)
    assert reading.generation_w > 0.0


def test_energy_reading_is_tagged_simulated():
    provider = SimulationTelemetryProvider()
    at = datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc)
    reading = provider.get_current_energy_reading(MICROGRID_ID)
    assert reading.source == TelemetrySource.SIMULATED
    historical = provider._energy_reading_at(MICROGRID_ID, at)
    assert historical.source == TelemetrySource.SIMULATED


def test_grid_import_export_are_mutually_exclusive_and_non_negative():
    provider = SimulationTelemetryProvider()
    for hour in [0, 6, 9, 12, 15, 19, 22]:
        at = datetime(2026, 6, 15, hour, 0, tzinfo=timezone.utc)
        reading = provider._energy_reading_at(MICROGRID_ID, at)
        assert reading.grid_import_w >= 0.0
        assert reading.grid_export_w >= 0.0
        assert reading.grid_import_w == 0.0 or reading.grid_export_w == 0.0


def test_battery_soc_within_bounds():
    provider = SimulationTelemetryProvider()
    for hour in range(0, 24, 2):
        at = datetime(2026, 6, 15, hour, 0, tzinfo=timezone.utc)
        reading = provider._energy_reading_at(MICROGRID_ID, at)
        assert 0.0 <= reading.battery_soc_percent <= 100.0


def test_energy_balance_invariant_holds_across_the_day():
    """
    Regression test for the telemetry consistency review: supply
    (generation + battery discharge + grid import) must equal demand
    (consumption + battery charge + grid export) at every timestamp,
    including when the battery is charging or discharging.
    """
    provider = SimulationTelemetryProvider()
    for hour in range(0, 24):
        for minute in (0, 15, 30, 45):
            at = datetime(2026, 6, 15, hour, minute, tzinfo=timezone.utc)
            reading = provider._energy_reading_at(MICROGRID_ID, at)

            battery_discharge = max(0.0, reading.battery_power_w)
            battery_charge = max(0.0, -reading.battery_power_w)

            supply = reading.generation_w + battery_discharge + reading.grid_import_w
            demand = reading.consumption_w + battery_charge + reading.grid_export_w

            assert supply == pytest.approx(demand, abs=0.05), (
                f"Energy balance violated at {at}: supply={supply}, demand={demand}, reading={reading}"
            )


def test_battery_power_w_is_present_and_signed():
    provider = SimulationTelemetryProvider()
    readings = [
        provider._energy_reading_at(MICROGRID_ID, datetime(2026, 6, 15, h, 0, tzinfo=timezone.utc))
        for h in range(24)
    ]
    assert all(r.battery_power_w is not None for r in readings)
    # Over a full day the battery should both charge (negative) and
    # discharge (positive) at some point, given the sinusoidal SOC model.
    assert any(r.battery_power_w > 0 for r in readings)
    assert any(r.battery_power_w < 0 for r in readings)


def test_historical_energy_readings_cover_requested_range():
    provider = SimulationTelemetryProvider()
    start = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 2, 0, tzinfo=timezone.utc)
    readings = provider.get_historical_energy_readings(MICROGRID_ID, start, end, interval_minutes=30)
    assert len(readings) == 5  # 0:00, 0:30, 1:00, 1:30, 2:00
    assert all(r.source == TelemetrySource.SIMULATED for r in readings)
    assert readings == sorted(readings, key=lambda r: r.recorded_at)


def test_device_reading_deterministic_and_tagged():
    provider = SimulationTelemetryProvider()
    at = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    first = provider._device_reading_at(DEVICE_ID, DeviceType.SOLAR_INVERTER, at)
    second = provider._device_reading_at(DEVICE_ID, DeviceType.SOLAR_INVERTER, at)
    assert first == second
    assert first.source == TelemetrySource.SIMULATED
    assert first.status in (DeviceStatus.ONLINE, DeviceStatus.OFFLINE)


def test_device_reading_voltage_is_plausible():
    provider = SimulationTelemetryProvider()
    at = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    reading = provider._device_reading_at(DEVICE_ID, DeviceType.METER, at)
    assert 200.0 <= reading.voltage_v <= 260.0
