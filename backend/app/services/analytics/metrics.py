"""
Energy metric calculations.

Pure functions operating on ordered lists of `EnergyReading` rows. No
database or HTTP concerns live here — this module is reusable by the
analytics service today and, unmodified, by future forecasting/decision
code that needs the same derived quantities.

Readings store instantaneous power (W); energy (Wh) is obtained by
trapezoidal integration over time, which is more accurate than naive
"power * fixed interval" when readings are unevenly spaced (e.g. after a
gap in ingestion).
"""
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from app.models.telemetry import EnergyReading


def _trapezoidal_wh(timestamps: Sequence[datetime], values_w: Sequence[float]) -> float:
    """Integrate a power series (W) over time (via timestamps) into energy (Wh)."""
    if len(timestamps) < 2:
        return 0.0
    total_wh = 0.0
    for i in range(1, len(timestamps)):
        dt_hours = (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600.0
        if dt_hours <= 0:
            continue
        avg_power = (values_w[i - 1] + values_w[i]) / 2.0
        total_wh += avg_power * dt_hours
    return total_wh


@dataclass(frozen=True)
class EnergySummary:
    start: datetime
    end: datetime
    reading_count: int

    total_consumption_wh: float
    total_generation_wh: float
    solar_self_consumption_wh: float
    grid_import_wh: float
    grid_export_wh: float

    peak_demand_w: float
    average_demand_w: float
    load_factor: Optional[float]  # average / peak, in [0, 1]

    renewable_contribution_pct: Optional[float]  # solar self-consumption / total consumption
    grid_dependency_pct: Optional[float]  # grid import / total consumption

    battery_charge_wh: Optional[float]
    battery_discharge_wh: Optional[float]
    battery_throughput_wh: Optional[float]


def compute_energy_summary(readings: List[EnergyReading]) -> EnergySummary:
    timestamps = [r.recorded_at for r in readings]
    consumption = [r.consumption_w for r in readings]
    generation = [r.generation_w for r in readings]
    grid_import = [r.grid_import_w for r in readings]
    grid_export = [r.grid_export_w for r in readings]
    self_consumption = [min(c, g) for c, g in zip(consumption, generation)]

    total_consumption_wh = _trapezoidal_wh(timestamps, consumption)
    total_generation_wh = _trapezoidal_wh(timestamps, generation)
    solar_self_consumption_wh = _trapezoidal_wh(timestamps, self_consumption)
    grid_import_wh = _trapezoidal_wh(timestamps, grid_import)
    grid_export_wh = _trapezoidal_wh(timestamps, grid_export)

    peak_demand_w = max(consumption)
    average_demand_w = statistics.fmean(consumption)
    load_factor = (average_demand_w / peak_demand_w) if peak_demand_w > 0 else None

    renewable_contribution_pct = (
        (solar_self_consumption_wh / total_consumption_wh) * 100.0 if total_consumption_wh > 0 else None
    )
    grid_dependency_pct = (grid_import_wh / total_consumption_wh) * 100.0 if total_consumption_wh > 0 else None

    battery_powers = [r.battery_power_w for r in readings if r.battery_power_w is not None]
    battery_charge_wh: Optional[float] = None
    battery_discharge_wh: Optional[float] = None
    battery_throughput_wh: Optional[float] = None
    if len(battery_powers) == len(readings) and len(readings) >= 2:
        charge_series = [max(0.0, -r.battery_power_w) for r in readings]
        discharge_series = [max(0.0, r.battery_power_w) for r in readings]
        battery_charge_wh = _trapezoidal_wh(timestamps, charge_series)
        battery_discharge_wh = _trapezoidal_wh(timestamps, discharge_series)
        battery_throughput_wh = battery_charge_wh + battery_discharge_wh

    return EnergySummary(
        start=timestamps[0],
        end=timestamps[-1],
        reading_count=len(readings),
        total_consumption_wh=round(total_consumption_wh, 2),
        total_generation_wh=round(total_generation_wh, 2),
        solar_self_consumption_wh=round(solar_self_consumption_wh, 2),
        grid_import_wh=round(grid_import_wh, 2),
        grid_export_wh=round(grid_export_wh, 2),
        peak_demand_w=round(peak_demand_w, 2),
        average_demand_w=round(average_demand_w, 2),
        load_factor=round(load_factor, 4) if load_factor is not None else None,
        renewable_contribution_pct=round(renewable_contribution_pct, 2) if renewable_contribution_pct is not None else None,
        grid_dependency_pct=round(grid_dependency_pct, 2) if grid_dependency_pct is not None else None,
        battery_charge_wh=round(battery_charge_wh, 2) if battery_charge_wh is not None else None,
        battery_discharge_wh=round(battery_discharge_wh, 2) if battery_discharge_wh is not None else None,
        battery_throughput_wh=round(battery_throughput_wh, 2) if battery_throughput_wh is not None else None,
    )
