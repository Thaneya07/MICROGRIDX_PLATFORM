"""
Consumption pattern analysis.

Statistics-based (not ML) pattern detection over persisted telemetry:
hourly consumption shape, weekday vs weekend behaviour, peak-demand
periods, base-load estimation, variability, and the solar/load
relationship. Every number here is computed directly from the readings
passed in — nothing is a fixed/hard-coded assumption about the customer.
"""
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models.telemetry import EnergyReading


@dataclass(frozen=True)
class HourlyPattern:
    hour: int  # 0-23, UTC
    average_consumption_w: float
    average_generation_w: float
    sample_count: int


@dataclass(frozen=True)
class PeakPeriod:
    hour: int
    average_consumption_w: float


@dataclass(frozen=True)
class ConsumptionPatterns:
    reading_count: int
    hourly_patterns: List[HourlyPattern]
    weekday_average_consumption_w: Optional[float]
    weekend_average_consumption_w: Optional[float]
    peak_periods: List[PeakPeriod]
    base_load_w: float
    consumption_variability: float  # coefficient of variation (stdev / mean)
    solar_load_correlation: Optional[float]  # Pearson correlation, generation vs consumption
    grid_import_wh_share_pct: Optional[float]  # share of consumption served by grid import, by energy
    battery_active_fraction: Optional[float]  # fraction of readings where the battery is charging or discharging


def _group_by_hour(readings: List[EnergyReading]) -> Dict[int, List[EnergyReading]]:
    groups: Dict[int, List[EnergyReading]] = {h: [] for h in range(24)}
    for r in readings:
        groups[r.recorded_at.hour].append(r)
    return groups


def compute_hourly_patterns(readings: List[EnergyReading]) -> List[HourlyPattern]:
    groups = _group_by_hour(readings)
    patterns = []
    for hour in range(24):
        bucket = groups[hour]
        if not bucket:
            continue
        patterns.append(
            HourlyPattern(
                hour=hour,
                average_consumption_w=round(statistics.fmean(r.consumption_w for r in bucket), 2),
                average_generation_w=round(statistics.fmean(r.generation_w for r in bucket), 2),
                sample_count=len(bucket),
            )
        )
    return patterns


def compute_peak_periods(hourly_patterns: List[HourlyPattern], top_n: int = 3) -> List[PeakPeriod]:
    """
    Peak periods are the hours whose average consumption is both among the
    highest observed and meaningfully above the mean (mean + 0.5 stdev),
    so a nearly-flat load profile correctly reports no distinct peaks
    rather than fabricating them.
    """
    if not hourly_patterns:
        return []
    values = [p.average_consumption_w for p in hourly_patterns]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    if stdev == 0:
        return []  # perfectly flat load profile has no meaningful peak
    threshold = mean + 0.5 * stdev

    candidates = [p for p in hourly_patterns if p.average_consumption_w >= threshold]
    candidates.sort(key=lambda p: p.average_consumption_w, reverse=True)
    return [PeakPeriod(hour=p.hour, average_consumption_w=p.average_consumption_w) for p in candidates[:top_n]]


def compute_base_load_w(readings: List[EnergyReading]) -> float:
    """Base load is estimated as the 10th percentile of observed consumption."""
    values = sorted(r.consumption_w for r in readings)
    if len(values) == 1:
        return round(values[0], 2)
    quantiles = statistics.quantiles(values, n=10, method="inclusive")
    return round(quantiles[0], 2)  # 10th percentile


def compute_consumption_variability(readings: List[EnergyReading]) -> float:
    values = [r.consumption_w for r in readings]
    mean = statistics.fmean(values)
    if mean == 0 or len(values) < 2:
        return 0.0
    stdev = statistics.pstdev(values)
    return round(stdev / mean, 4)


def compute_solar_load_correlation(readings: List[EnergyReading]) -> Optional[float]:
    if len(readings) < 3:
        return None
    generation = [r.generation_w for r in readings]
    consumption = [r.consumption_w for r in readings]
    if len(set(generation)) < 2 or len(set(consumption)) < 2:
        # statistics.correlation is undefined when a series has zero variance.
        return None
    return round(statistics.correlation(generation, consumption), 4)


def compute_weekday_weekend_averages(readings: List[EnergyReading]) -> tuple[Optional[float], Optional[float]]:
    weekday_values = [r.consumption_w for r in readings if r.recorded_at.weekday() < 5]
    weekend_values = [r.consumption_w for r in readings if r.recorded_at.weekday() >= 5]
    weekday_avg = round(statistics.fmean(weekday_values), 2) if weekday_values else None
    weekend_avg = round(statistics.fmean(weekend_values), 2) if weekend_values else None
    return weekday_avg, weekend_avg


def compute_battery_active_fraction(readings: List[EnergyReading]) -> Optional[float]:
    powers = [r.battery_power_w for r in readings if r.battery_power_w is not None]
    if len(powers) != len(readings) or not readings:
        return None
    active = sum(1 for p in powers if abs(p) > 1.0)
    return round(active / len(powers), 4)


def analyze_consumption_patterns(readings: List[EnergyReading]) -> ConsumptionPatterns:
    hourly = compute_hourly_patterns(readings)
    weekday_avg, weekend_avg = compute_weekday_weekend_averages(readings)

    total_consumption_wh_proxy = sum(r.consumption_w for r in readings)
    total_grid_import_proxy = sum(r.grid_import_w for r in readings)
    grid_import_share_pct = (
        round((total_grid_import_proxy / total_consumption_wh_proxy) * 100.0, 2)
        if total_consumption_wh_proxy > 0
        else None
    )

    return ConsumptionPatterns(
        reading_count=len(readings),
        hourly_patterns=hourly,
        weekday_average_consumption_w=weekday_avg,
        weekend_average_consumption_w=weekend_avg,
        peak_periods=compute_peak_periods(hourly),
        base_load_w=compute_base_load_w(readings),
        consumption_variability=compute_consumption_variability(readings),
        solar_load_correlation=compute_solar_load_correlation(readings),
        grid_import_wh_share_pct=grid_import_share_pct,
        battery_active_fraction=compute_battery_active_fraction(readings),
    )
