"""
Decision evaluator.

Turns a raw OptimizerSolution into a human-facing recommendation:
classifies the immediate (first-step) recommended battery action,
computes expected aggregate outcomes over the horizon, and checks each
safety constraint explicitly (rather than only trusting the solver did
not violate a bound — every constraint is independently re-verified here
so a future change to the optimizer cannot silently produce an
unverified "OPTIMAL" result).
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.models.decision import BatteryAction
from app.services.decision.constraints import BatteryConstraints
from app.services.decision.optimizer import OptimizerSolution

_TOLERANCE_W = 1.0
_TOLERANCE_WH = 1.0


@dataclass(frozen=True)
class ConstraintCheck:
    name: str
    satisfied: bool
    detail: str


@dataclass(frozen=True)
class EvaluationResult:
    battery_action: BatteryAction
    battery_power_w: float  # magnitude; sign encoded by battery_action
    expected_grid_import_wh: float
    expected_grid_export_wh: float
    expected_renewable_utilization_pct: Optional[float]
    expected_peak_w: float
    constraint_checks: List[ConstraintCheck]
    all_constraints_satisfied: bool


def _energy_wh(series_w: List[float], interval_minutes: int) -> float:
    dt_hours = interval_minutes / 60.0
    return sum(v * dt_hours for v in series_w)


def check_constraints(solution: OptimizerSolution, constraints: BatteryConstraints) -> List[ConstraintCheck]:
    checks: List[ConstraintCheck] = []

    soc_ok = all(
        constraints.min_soc_wh - _TOLERANCE_WH <= s <= constraints.max_soc_wh + _TOLERANCE_WH
        for s in solution.soc_wh
    )
    checks.append(
        ConstraintCheck(
            name="battery_soc_within_bounds",
            satisfied=soc_ok,
            detail=f"SOC must stay within [{constraints.min_soc_wh:.0f}, {constraints.max_soc_wh:.0f}] Wh "
            f"({constraints.min_soc_percent:.0f}-{constraints.max_soc_percent:.0f}%).",
        )
    )

    charge_ok = all(0.0 - _TOLERANCE_W <= c <= constraints.max_charge_w + _TOLERANCE_W for c in solution.charge_w)
    checks.append(
        ConstraintCheck(
            name="charge_power_within_limit",
            satisfied=charge_ok,
            detail=f"Charge power must not exceed {constraints.max_charge_w:.0f} W.",
        )
    )

    discharge_ok = all(
        0.0 - _TOLERANCE_W <= d <= constraints.max_discharge_w + _TOLERANCE_W for d in solution.discharge_w
    )
    checks.append(
        ConstraintCheck(
            name="discharge_power_within_limit",
            satisfied=discharge_ok,
            detail=f"Discharge power must not exceed {constraints.max_discharge_w:.0f} W.",
        )
    )

    no_simultaneous = all(
        not (c > _TOLERANCE_W and d > _TOLERANCE_W) for c, d in zip(solution.charge_w, solution.discharge_w)
    )
    checks.append(
        ConstraintCheck(
            name="no_simultaneous_charge_discharge",
            satisfied=no_simultaneous,
            detail="Battery must not charge and discharge in the same interval.",
        )
    )

    non_negative = all(
        v >= -_TOLERANCE_W
        for series in (solution.charge_w, solution.discharge_w, solution.grid_import_w, solution.grid_export_w)
        for v in series
    )
    checks.append(
        ConstraintCheck(
            name="non_negative_power_flows",
            satisfied=non_negative,
            detail="Charge/discharge/grid import/export must all be physically non-negative.",
        )
    )

    return checks


def evaluate_solution(
    solution: OptimizerSolution,
    constraints: BatteryConstraints,
    interval_minutes: int,
    total_consumption_wh: float,
) -> EvaluationResult:
    checks = check_constraints(solution, constraints)
    all_satisfied = all(c.satisfied for c in checks)

    # Immediate (first-step) recommendation is what gets surfaced as "the"
    # recommendation — the rest of the horizon informs the explanation but
    # a receding-horizon optimizer is re-solved on the next run anyway
    # (see service.py), so only the first step is actionable right now.
    first_charge = solution.charge_w[0] if solution.charge_w else 0.0
    first_discharge = solution.discharge_w[0] if solution.discharge_w else 0.0

    if first_charge > _TOLERANCE_W:
        action = BatteryAction.CHARGE
        power = first_charge
    elif first_discharge > _TOLERANCE_W:
        action = BatteryAction.DISCHARGE
        power = first_discharge
    else:
        action = BatteryAction.IDLE
        power = 0.0

    grid_import_wh = _energy_wh(solution.grid_import_w, interval_minutes)
    grid_export_wh = _energy_wh(solution.grid_export_w, interval_minutes)

    renewable_pct: Optional[float] = None
    if total_consumption_wh > 0:
        self_consumed_wh = max(0.0, total_consumption_wh - grid_import_wh)
        renewable_pct = min(100.0, (self_consumed_wh / total_consumption_wh) * 100.0)

    return EvaluationResult(
        battery_action=action,
        battery_power_w=power,
        expected_grid_import_wh=grid_import_wh,
        expected_grid_export_wh=grid_export_wh,
        expected_renewable_utilization_pct=renewable_pct,
        expected_peak_w=solution.peak_w or 0.0,
        constraint_checks=checks,
        all_constraints_satisfied=all_satisfied,
    )
