"""
Load recommendations and human-readable explanations.

Load recommendations are rule-based, not part of the continuous LP: the
current Load model records priority/controllability/status but not a
continuous power draw suitable for a scheduling variable, so treating
loads as LP decision variables would require inventing per-load power
data that does not exist. Per Step 7 spec section 8, rules are the
correct tool here, layered on top of the LP's battery/grid results.

PRIORITY CONVENTION (the Load model stores `priority` as a plain
integer with no built-in ordering semantics): this module treats a
HIGHER integer as MORE important/critical, i.e. protected first and
deferred last. This is a documented assumption, not a value defined by
the existing schema — if the project later formalizes a
CRITICAL/HIGH/MEDIUM/LOW enum, this is the only place that needs to
change.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.models.decision import BatteryAction
from app.models.load import Load
from app.services.decision.evaluator import EvaluationResult

_DEFER_CANDIDATE_LIMIT = 3
_RUN_NOW_CANDIDATE_LIMIT = 3


@dataclass(frozen=True)
class LoadRecommendation:
    load_id: str
    load_name: str
    action: str  # "DEFER", "RUN_NOW", "MAINTAIN"
    reason: str
    priority: int


def build_load_recommendations(loads: List[Load], evaluation: EvaluationResult) -> List[LoadRecommendation]:
    recommendations: List[LoadRecommendation] = []

    controllable_on = sorted(
        [l for l in loads if l.controllable and l.status.value == "ON"], key=lambda l: l.priority
    )
    controllable_off = sorted(
        [l for l in loads if l.controllable and l.status.value == "OFF"], key=lambda l: l.priority
    )

    under_pressure = evaluation.battery_action == BatteryAction.DISCHARGE or evaluation.expected_peak_w > 0
    has_surplus = (
        evaluation.battery_action == BatteryAction.CHARGE and evaluation.expected_grid_export_wh > 0
    )

    if under_pressure:
        for load in controllable_on[:_DEFER_CANDIDATE_LIMIT]:
            recommendations.append(
                LoadRecommendation(
                    load_id=str(load.id),
                    load_name=load.name,
                    action="DEFER",
                    reason=(
                        f"Forecasted conditions require battery discharge or elevated grid import; "
                        f"'{load.name}' is controllable and lower priority ({load.priority}), so deferring it "
                        f"reduces demand during this constrained period."
                    ),
                    priority=load.priority,
                )
            )
    elif has_surplus:
        for load in controllable_off[:_RUN_NOW_CANDIDATE_LIMIT]:
            recommendations.append(
                LoadRecommendation(
                    load_id=str(load.id),
                    load_name=load.name,
                    action="RUN_NOW",
                    reason=(
                        f"Forecasted solar generation exceeds what the battery can absorb (expected grid export "
                        f"{evaluation.expected_grid_export_wh:.0f} Wh over the horizon); running '{load.name}' now "
                        f"uses otherwise-exported renewable energy instead of curtailing/exporting it."
                    ),
                    priority=load.priority,
                )
            )

    # Any load not already given an active recommendation is explicitly
    # reported as maintained, so the API response is never silent about a
    # load that exists but wasn't touched.
    handled_ids = {r.load_id for r in recommendations}
    for load in loads:
        if str(load.id) not in handled_ids:
            recommendations.append(
                LoadRecommendation(
                    load_id=str(load.id),
                    load_name=load.name,
                    action="MAINTAIN",
                    reason="No change recommended for this load under current forecasted conditions.",
                    priority=load.priority,
                )
            )

    return recommendations


def build_explanation(
    evaluation: EvaluationResult,
    demand_series: Optional[List[float]],
    solar_series: Optional[List[float]],
    current_soc_percent: Optional[float],
    constraints_max_soc: float,
    constraints_min_soc: float,
) -> str:
    """Builds an explanation strictly from the actual evaluation result and inputs — never a generic template unrelated to the outcome."""
    soc_str = f"{current_soc_percent:.0f}%" if current_soc_percent is not None else "unknown"

    if evaluation.battery_action == BatteryAction.CHARGE:
        solar_note = ""
        if solar_series:
            peak_solar = max(solar_series)
            solar_note = f" Forecasted solar generation reaches up to {peak_solar:.0f} W within the horizon."
        return (
            f"Battery charging recommended at {evaluation.battery_power_w:.0f} W: current SOC ({soc_str}) is "
            f"below the configured maximum ({constraints_max_soc:.0f}%), and available/forecasted generation "
            f"supports charging without increasing grid import.{solar_note}"
        )

    if evaluation.battery_action == BatteryAction.DISCHARGE:
        demand_note = ""
        if demand_series:
            peak_demand = max(demand_series)
            demand_note = f" Forecasted demand reaches up to {peak_demand:.0f} W within the horizon."
        return (
            f"Battery discharge recommended at {evaluation.battery_power_w:.0f} W: this reduces expected grid "
            f"import (expected {evaluation.expected_grid_import_wh:.0f} Wh over the horizon) while current SOC "
            f"({soc_str}) remains above the configured minimum ({constraints_min_soc:.0f}%).{demand_note}"
        )

    return (
        f"No battery action recommended: charging or discharging would not improve the optimization objective "
        f"given forecasted generation and demand, or would risk violating the configured SOC range "
        f"({constraints_min_soc:.0f}-{constraints_max_soc:.0f}%). Current SOC is {soc_str}."
    )
