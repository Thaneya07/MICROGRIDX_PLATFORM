"""
Simulation telemetry provider.

Generates realistic, deterministic, time-dependent energy data — solar
generation curves, morning/evening consumption peaks, grid import/export,
and a bounded battery state-of-charge trajectory — instead of meaningless
per-request random numbers.

Determinism: for a given (microgrid_id, calendar day) a fixed "day profile"
(peak solar output, cloudiness, load scale) is derived from a seed. Within
that day, values are a smooth deterministic function of time-of-day plus a
small amount of seeded per-minute jitter, so:

  * repeated calls for the same minute return the same numbers
  * calls for nearby minutes return smoothly varying, physically plausible
    numbers (no jumping randomly between requests)
  * different days/microgrids produce different but still realistic
    "weather"

Every value returned is tagged `TelemetrySource.SIMULATED` — this provider
must never be mistaken for a real sensor feed.
"""
import hashlib
import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from app.core.config import get_settings
from app.models.device import DeviceStatus, DeviceType
from app.models.telemetry import TelemetrySource
from app.services.telemetry.base import DeviceReadingData, EnergyReadingData, TelemetryProvider

settings = get_settings()


def _day_seed(entity_id: uuid.UUID, day: datetime, salt: str = "") -> int:
    """Deterministic integer seed for a given entity + calendar day (+ optional salt)."""
    key = f"{settings.SIMULATION_SEED}:{entity_id}:{day.date().isoformat()}:{salt}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _minute_seed(entity_id: uuid.UUID, at: datetime, salt: str = "") -> int:
    """Deterministic integer seed for a given entity + specific minute (+ optional salt)."""
    minute_bucket = at.replace(second=0, microsecond=0)
    key = f"{settings.SIMULATION_SEED}:{entity_id}:{minute_bucket.isoformat()}:{salt}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _gaussian_bump(t_hours: float, center: float, width: float, amplitude: float) -> float:
    return amplitude * math.exp(-((t_hours - center) ** 2) / (2 * width**2))


class _DayProfile:
    """Per-(entity, day) randomized-but-fixed parameters describing that day's conditions."""

    __slots__ = ("peak_solar_w", "cloudiness", "load_scale", "morning_scale", "evening_scale")

    def __init__(self, entity_id: uuid.UUID, day: datetime, salt: str = ""):
        rng = random.Random(_day_seed(entity_id, day, salt))
        self.peak_solar_w = rng.uniform(0.75, 1.0) * settings.SIMULATED_PEAK_SOLAR_W
        self.cloudiness = rng.uniform(0.0, 0.35)  # fraction of solar lost to cloud cover that day
        self.load_scale = rng.uniform(0.85, 1.15)
        self.morning_scale = rng.uniform(0.8, 1.2)
        self.evening_scale = rng.uniform(0.8, 1.2)


def _solar_generation_w(t_hours: float, profile: "_DayProfile") -> float:
    sunrise, sunset = 6.0, 18.5
    if t_hours <= sunrise or t_hours >= sunset:
        return 0.0
    span = sunset - sunrise
    shape = math.sin(math.pi * (t_hours - sunrise) / span)
    return max(0.0, profile.peak_solar_w * shape * (1 - profile.cloudiness))


def _consumption_w(t_hours: float, profile: "_DayProfile") -> float:
    base_load = settings.SIMULATED_BASE_LOAD_W * profile.load_scale
    morning = _gaussian_bump(t_hours, center=8.0, width=1.2, amplitude=settings.SIMULATED_MORNING_PEAK_W) * profile.morning_scale
    evening = _gaussian_bump(t_hours, center=19.5, width=1.5, amplitude=settings.SIMULATED_EVENING_PEAK_W) * profile.evening_scale
    return max(0.0, base_load + morning + evening)


def _battery_soc_percent(t_hours: float) -> float:
    # Smooth bounded trajectory: charges through the solar-rich midday window,
    # discharges through the evening peak, drifts back overnight.
    soc = 55.0 + 30.0 * math.sin(2 * math.pi * (t_hours - 9.0) / 24.0)
    return max(15.0, min(95.0, soc))


def _jitter(entity_id: uuid.UUID, at: datetime, salt: str, magnitude: float) -> float:
    rng = random.Random(_minute_seed(entity_id, at, salt))
    return rng.uniform(-magnitude, magnitude)


def _device_type_power_profile(device_type: DeviceType, t_hours: float, profile: "_DayProfile") -> float:
    """Rough per-device-type power draw/output, used only for device-level simulation."""
    if device_type == DeviceType.SOLAR_INVERTER:
        return _solar_generation_w(t_hours, profile)
    if device_type == DeviceType.BATTERY:
        # Positive = discharging (supplying power), negative = charging.
        soc_now = _battery_soc_percent(t_hours)
        soc_prev = _battery_soc_percent(t_hours - (1 / 60))
        trend = soc_now - soc_prev
        return -trend * 200.0  # scale trend into a plausible watt range
    if device_type in (DeviceType.LOAD_CONTROLLER, DeviceType.OTHER):
        return _consumption_w(t_hours, profile) * 0.15
    if device_type == DeviceType.METER:
        return _consumption_w(t_hours, profile)
    # SENSOR and anything else: negligible draw
    return 1.5


class SimulationTelemetryProvider(TelemetryProvider):
    """Deterministic, seeded simulation of realistic microgrid/device energy behaviour."""

    def get_current_energy_reading(self, microgrid_id: uuid.UUID) -> EnergyReadingData:
        now = datetime.now(timezone.utc)
        return self._energy_reading_at(microgrid_id, now)

    def get_historical_energy_readings(
        self, microgrid_id: uuid.UUID, start: datetime, end: datetime, interval_minutes: int
    ) -> List[EnergyReadingData]:
        return [
            self._energy_reading_at(microgrid_id, ts)
            for ts in self._time_range(start, end, interval_minutes)
        ]

    def get_current_device_reading(self, device_id: uuid.UUID, device_type: str) -> DeviceReadingData:
        now = datetime.now(timezone.utc)
        return self._device_reading_at(device_id, DeviceType(device_type), now)

    def get_historical_device_readings(
        self, device_id: uuid.UUID, device_type: str, start: datetime, end: datetime, interval_minutes: int
    ) -> List[DeviceReadingData]:
        dtype = DeviceType(device_type)
        return [
            self._device_reading_at(device_id, dtype, ts)
            for ts in self._time_range(start, end, interval_minutes)
        ]

    # --- internal helpers ---

    @staticmethod
    def _time_range(start: datetime, end: datetime, interval_minutes: int) -> List[datetime]:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        step = timedelta(minutes=max(1, interval_minutes))
        points = []
        cursor = start
        while cursor <= end:
            points.append(cursor)
            cursor += step
        return points

    def _energy_reading_at(self, microgrid_id: uuid.UUID, at: datetime) -> EnergyReadingData:
        profile = _DayProfile(microgrid_id, at)
        t_hours = at.hour + at.minute / 60 + at.second / 3600

        base_generation = _solar_generation_w(t_hours, profile)
        generation = base_generation + _jitter(microgrid_id, at, "gen", 15.0) if base_generation > 0 else 0.0
        generation = max(0.0, generation)

        consumption = _consumption_w(t_hours, profile) + _jitter(microgrid_id, at, "load", 20.0)
        consumption = max(0.0, consumption)

        grid_import = max(0.0, consumption - generation)
        grid_export = max(0.0, generation - consumption)

        soc = _battery_soc_percent(t_hours)
        battery_available_w = settings.SIMULATED_BATTERY_CAPACITY_W * max(0.0, (soc - 20.0) / 100.0)
        available_energy = generation + battery_available_w

        return EnergyReadingData(
            microgrid_id=microgrid_id,
            recorded_at=at,
            consumption_w=round(consumption, 2),
            generation_w=round(generation, 2),
            grid_import_w=round(grid_import, 2),
            grid_export_w=round(grid_export, 2),
            available_energy_w=round(available_energy, 2),
            battery_soc_percent=round(soc, 2),
            source=TelemetrySource.SIMULATED,
        )

    def _device_reading_at(self, device_id: uuid.UUID, device_type: DeviceType, at: datetime) -> DeviceReadingData:
        profile = _DayProfile(device_id, at, salt="device")
        t_hours = at.hour + at.minute / 60 + at.second / 3600

        power = _device_type_power_profile(device_type, t_hours, profile) + _jitter(device_id, at, "device", 5.0)
        power = max(0.0, power)

        voltage = 230.0 + _jitter(device_id, at, "voltage", 3.0)
        current = power / voltage if voltage > 0 else 0.0
        status = DeviceStatus.ONLINE if power > 0.5 or device_type == DeviceType.SENSOR else DeviceStatus.OFFLINE

        return DeviceReadingData(
            device_id=device_id,
            recorded_at=at,
            power_w=round(power, 2),
            voltage_v=round(voltage, 2),
            current_a=round(current, 3),
            status=status,
            source=TelemetrySource.SIMULATED,
        )
