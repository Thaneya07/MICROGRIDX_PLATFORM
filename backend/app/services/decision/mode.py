"""
Operating mode classification.

Fulfills the Phase 1 `DecisionEngine.evaluate_mode` contract
(app/services/decision_engine.py — `OperatingMode` is reused unmodified
from there, not redefined, to keep a single source of truth for the enum
across the codebase).

This is a deterministic, rule-based classification layered on top of the
LP optimizer's output — not a separate model. Rules are used here exactly
as the Step 7 spec intends: as safety/interpretation logic on top of an
already-computed, explainable optimization result — not as the primary
optimizer.

RULES (in priority order — first match wins):

1. EMERGENCY_MODE if the optimizer fell back (no trustworthy
   recommendation exists) or a safety constraint was violated.
2. EMERGENCY_MODE if current battery SOC is at or below the configured
   minimum plus a small buffer (DECISION_EMERGENCY_SOC_BUFFER_PERCENT).
3. ECO_MODE if the recommendation defers any load, or recommends battery
   discharge.
4. NORMAL_MODE otherwise.
"""
from dataclasses import dataclass
from typing import List, Optional

from app.services.decision_engine import OperatingMode
from app.services.decision.evaluator import EvaluationResult
from app.services.decision.recommendations import LoadRecommendation


@dataclass(frozen=True)
class ModeClassification:
    mode: OperatingMode
    reason: str


def classify_operating_mode(
    evaluation: Optional[EvaluationResult],
    load_recommendations: List[LoadRecommendation],
    current_soc_percent: Optional[float],
    min_soc_percent: float,
    emergency_buffer_percent: float,
    fallback_used: bool,
) -> ModeClassification:
    if fallback_used or evaluation is None:
        return ModeClassification(
            mode=OperatingMode.EMERGENCY_MODE,
            reason="No trustworthy optimization result is available (fallback was used), so the system is "
            "treated as constrained until telemetry/forecast data is sufficient again.",
        )

    if not evaluation.all_constraints_satisfied:
        failed = [c.name for c in evaluation.constraint_checks if not c.satisfied]
        return ModeClassification(
            mode=OperatingMode.EMERGENCY_MODE,
            reason=f"One or more safety constraints were violated by the optimization result ({', '.join(failed)}), "
            "so the system is treated as constrained regardless of the recommendation.",
        )

    emergency_threshold = min_soc_percent + emergency_buffer_percent
    if current_soc_percent is not None and current_soc_percent <= emergency_threshold:
        return ModeClassification(
            mode=OperatingMode.EMERGENCY_MODE,
            reason=f"Current battery SOC ({current_soc_percent:.0f}%) is at or below the emergency threshold "
            f"({emergency_threshold:.0f}% = configured minimum {min_soc_percent:.0f}% + "
            f"{emergency_buffer_percent:.0f}% buffer).",
        )

    deferred = [r for r in load_recommendations if r.action == "DEFER"]
    if deferred:
        names = ", ".join(r.load_name for r in deferred)
        return ModeClassification(
            mode=OperatingMode.ECO_MODE,
            reason=f"The recommendation defers {len(deferred)} controllable load(s) ({names}) to manage "
            "forecasted demand/grid pressure.",
        )

    from app.models.decision import BatteryAction

    if evaluation.battery_action == BatteryAction.DISCHARGE:
        return ModeClassification(
            mode=OperatingMode.ECO_MODE,
            reason=f"Battery discharge ({evaluation.battery_power_w:.0f} W) is recommended to reduce grid import, "
            "indicating the system is managing energy scarcity rather than operating freely.",
        )

    return ModeClassification(
        mode=OperatingMode.NORMAL_MODE,
        reason="No safety constraints are near their limits, no loads need to be deferred, and the battery is "
        "not being drawn down to cover demand — the system is operating within normal conditions.",
    )
