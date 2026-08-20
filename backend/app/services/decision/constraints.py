"""
Battery safety constraints for the optimizer.

Values are sourced from configuration (app/core/config.py), documented
there as explicit defaults rather than hardware-reported specs, since the
current device/telemetry model has no battery-capacity or power-limit
fields. If/when real battery management hardware reports these, this is
the single place to source them from a device/config lookup instead.
"""
from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class BatteryConstraints:
    capacity_wh: float
    min_soc_percent: float
    max_soc_percent: float
    max_charge_w: float
    max_discharge_w: float
    charge_efficiency: float
    discharge_efficiency: float

    @property
    def min_soc_wh(self) -> float:
        return self.capacity_wh * (self.min_soc_percent / 100.0)

    @property
    def max_soc_wh(self) -> float:
        return self.capacity_wh * (self.max_soc_percent / 100.0)


def get_battery_constraints() -> BatteryConstraints:
    return BatteryConstraints(
        capacity_wh=settings.DECISION_BATTERY_CAPACITY_WH,
        min_soc_percent=settings.DECISION_BATTERY_MIN_SOC_PERCENT,
        max_soc_percent=settings.DECISION_BATTERY_MAX_SOC_PERCENT,
        max_charge_w=settings.DECISION_BATTERY_MAX_CHARGE_W,
        max_discharge_w=settings.DECISION_BATTERY_MAX_DISCHARGE_W,
        charge_efficiency=settings.DECISION_BATTERY_CHARGE_EFFICIENCY,
        discharge_efficiency=settings.DECISION_BATTERY_DISCHARGE_EFFICIENCY,
    )
