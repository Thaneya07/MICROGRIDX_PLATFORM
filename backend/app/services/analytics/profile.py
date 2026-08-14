"""
Customer energy profile.

Combines outputs from `metrics.py` and `patterns.py` into a single
behavioural profile. Every descriptive characteristic attached to the
profile is derived from a numeric comparison against the data itself —
never a fixed/assumed label — and the numbers backing each characteristic
are included in the response so the classification is inspectable rather
than a black box.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from app.models.telemetry import EnergyReading
from app.services.analytics.metrics import EnergySummary, compute_energy_summary
from app.services.analytics.patterns import ConsumptionPatterns, analyze_consumption_patterns


@dataclass(frozen=True)
class UsageCharacteristic:
    label: str
    basis: str  # human-readable explanation of the numeric comparison behind the label


@dataclass(frozen=True)
class CustomerEnergyProfile:
    start: datetime
    end: datetime
    reading_count: int

    typical_consumption_w: float
    average_demand_w: float
    peak_demand_w: float
    peak_hour: Optional[int]

    solar_utilization_pct: Optional[float]
    grid_dependency_pct: Optional[float]
    load_variability: float

    characteristics: List[UsageCharacteristic]


# Thresholds are named constants rather than inline magic numbers, and are
# deliberately modest margins: a profile should only assert a
# characteristic when the data supports it clearly.
_PERIOD_DOMINANCE_MARGIN = 1.15  # one period must exceed the other by >=15% to call it "-heavy"
_HIGH_VARIABILITY_CV = 0.5
_LOW_VARIABILITY_CV = 0.15
_HIGH_GRID_DEPENDENCY_PCT = 70.0
_HIGH_SOLAR_UTILIZATION_PCT = 60.0


def _classify(patterns: ConsumptionPatterns, summary: EnergySummary) -> List[UsageCharacteristic]:
    characteristics: List[UsageCharacteristic] = []

    morning_hours = {h.hour: h for h in patterns.hourly_patterns if h.hour in range(6, 10)}
    evening_hours = {h.hour: h for h in patterns.hourly_patterns if h.hour in range(17, 22)}
    if morning_hours and evening_hours:
        morning_avg = sum(h.average_consumption_w for h in morning_hours.values()) / len(morning_hours)
        evening_avg = sum(h.average_consumption_w for h in evening_hours.values()) / len(evening_hours)
        if evening_avg >= morning_avg * _PERIOD_DOMINANCE_MARGIN:
            characteristics.append(
                UsageCharacteristic(
                    label="evening-heavy",
                    basis=f"Average evening (17:00-21:00) consumption {evening_avg:.0f}W exceeds "
                    f"average morning (06:00-09:00) consumption {morning_avg:.0f}W by "
                    f"{(evening_avg / morning_avg - 1) * 100:.0f}%.",
                )
            )
        elif morning_avg >= evening_avg * _PERIOD_DOMINANCE_MARGIN:
            characteristics.append(
                UsageCharacteristic(
                    label="morning-heavy",
                    basis=f"Average morning (06:00-09:00) consumption {morning_avg:.0f}W exceeds "
                    f"average evening (17:00-21:00) consumption {evening_avg:.0f}W by "
                    f"{(morning_avg / evening_avg - 1) * 100:.0f}%.",
                )
            )

    if patterns.consumption_variability >= _HIGH_VARIABILITY_CV:
        characteristics.append(
            UsageCharacteristic(
                label="high-variability",
                basis=f"Coefficient of variation of consumption is {patterns.consumption_variability:.2f}, "
                f"at or above the {_HIGH_VARIABILITY_CV:.2f} threshold.",
            )
        )
    elif patterns.consumption_variability <= _LOW_VARIABILITY_CV:
        characteristics.append(
            UsageCharacteristic(
                label="stable-load",
                basis=f"Coefficient of variation of consumption is {patterns.consumption_variability:.2f}, "
                f"at or below the {_LOW_VARIABILITY_CV:.2f} threshold.",
            )
        )

    if summary.grid_dependency_pct is not None and summary.grid_dependency_pct >= _HIGH_GRID_DEPENDENCY_PCT:
        characteristics.append(
            UsageCharacteristic(
                label="grid-dependent",
                basis=f"{summary.grid_dependency_pct:.0f}% of consumed energy was imported from the grid, "
                f"at or above the {_HIGH_GRID_DEPENDENCY_PCT:.0f}% threshold.",
            )
        )

    if (
        summary.renewable_contribution_pct is not None
        and summary.renewable_contribution_pct >= _HIGH_SOLAR_UTILIZATION_PCT
    ):
        characteristics.append(
            UsageCharacteristic(
                label="solar-dominant",
                basis=f"{summary.renewable_contribution_pct:.0f}% of consumed energy was self-generated solar, "
                f"at or above the {_HIGH_SOLAR_UTILIZATION_PCT:.0f}% threshold.",
            )
        )

    return characteristics


def build_customer_energy_profile(readings: List[EnergyReading]) -> CustomerEnergyProfile:
    summary = compute_energy_summary(readings)
    patterns = analyze_consumption_patterns(readings)

    peak_hour = patterns.peak_periods[0].hour if patterns.peak_periods else None

    return CustomerEnergyProfile(
        start=summary.start,
        end=summary.end,
        reading_count=summary.reading_count,
        typical_consumption_w=summary.average_demand_w,
        average_demand_w=summary.average_demand_w,
        peak_demand_w=summary.peak_demand_w,
        peak_hour=peak_hour,
        solar_utilization_pct=summary.renewable_contribution_pct,
        grid_dependency_pct=summary.grid_dependency_pct,
        load_variability=patterns.consumption_variability,
        characteristics=_classify(patterns, summary),
    )
