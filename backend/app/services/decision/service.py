"""
Decision service.

Orchestrates the full pipeline for one optimization run:

    OptimizationInputs (telemetry + forecast + loads)
        -> optimizer.solve_dispatch (LP)
        -> evaluator.evaluate_solution (constraint verification)
        -> recommendations.build_load_recommendations / build_explanation
        -> Decision row (persisted)

SAFETY: every method here returns a RECOMMENDATION. Nothing in this
module, or anywhere else in the codebase, sends a command to a physical
device. See docs/architecture for the full safety boundary statement.

FALLBACK: if forecast data is unavailable, the optimizer is never
invoked — a SAFE_FALLBACK Decision is persisted and returned instead,
with an explicit reason. This function never silently returns an
apparently-optimal decision when optimization did not actually run.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.decision import ApprovalStatus, BatteryAction, Decision, OptimizationStatus
from app.models.microgrid import Microgrid
from app.models.telemetry import TelemetrySource
from app.services.decision.constraints import get_battery_constraints
from app.services.decision.evaluator import evaluate_solution
from app.services.decision.inputs import gather_optimization_inputs
from app.services.decision.objective import get_objective_weights
from app.services.decision.optimizer import solve_dispatch
from app.services.decision.recommendations import build_explanation, build_load_recommendations
from app.services.decision.mode import classify_operating_mode
from app.services.telemetry.base import TelemetryProvider

settings = get_settings()
logger = get_logger(__name__)


class DecisionService:
    def __init__(self, db: Session, provider: TelemetryProvider):
        self.db = db
        self.provider = provider

    def optimize(self, microgrid_id: uuid.UUID, source: TelemetrySource) -> Decision:
        self._require_microgrid(microgrid_id)

        inputs = gather_optimization_inputs(self.db, self.provider, microgrid_id, source)

        if inputs.demand_forecast is None or inputs.solar_forecast is None:
            return self._persist_fallback(
                inputs,
                reason=inputs.forecast_unavailable_reason
                or "Forecast data unavailable for this microgrid/source; train a forecasting model first.",
            )

        constraints = get_battery_constraints()
        weights = get_objective_weights()

        current_soc_percent = inputs.current_battery_soc_percent
        if current_soc_percent is None:
            return self._persist_fallback(
                inputs, reason="No current battery state-of-charge reading is available for this microgrid."
            )
        current_soc_wh = constraints.capacity_wh * (current_soc_percent / 100.0)

        n = min(len(inputs.demand_forecast.values_w), len(inputs.solar_forecast.values_w), inputs.n_steps)
        if n == 0:
            return self._persist_fallback(inputs, reason="Forecast horizon returned zero usable steps.")

        demand_series = inputs.demand_forecast.values_w[:n]
        solar_series = inputs.solar_forecast.values_w[:n]

        solution = solve_dispatch(
            generation_w=solar_series,
            consumption_w=demand_series,
            current_soc_wh=current_soc_wh,
            interval_minutes=inputs.interval_minutes,
            constraints=constraints,
            weights=weights,
        )

        if not solution.success:
            return self._persist_fallback(
                inputs, reason=f"Optimizer did not find a feasible solution: {solution.status_message}"
            )

        total_consumption_wh = sum(v * (inputs.interval_minutes / 60.0) for v in demand_series)
        evaluation = evaluate_solution(solution, constraints, inputs.interval_minutes, total_consumption_wh)

        load_recs = build_load_recommendations(inputs.loads, evaluation)
        explanation = build_explanation(
            evaluation,
            demand_series,
            solar_series,
            current_soc_percent,
            constraints.max_soc_percent,
            constraints.min_soc_percent,
        )
        reason = self._short_reason(evaluation)

        mode_classification = classify_operating_mode(
            evaluation=evaluation,
            load_recommendations=load_recs,
            current_soc_percent=current_soc_percent,
            min_soc_percent=constraints.min_soc_percent,
            emergency_buffer_percent=settings.DECISION_EMERGENCY_SOC_BUFFER_PERCENT,
            fallback_used=False,
        )

        actual_horizon_end = datetime.fromtimestamp(
            inputs.horizon_start.timestamp() + n * inputs.interval_minutes * 60, tz=timezone.utc
        )

        row = Decision(
            microgrid_id=microgrid_id,
            source=source,
            optimization_status=OptimizationStatus.OPTIMAL
            if evaluation.all_constraints_satisfied
            else OptimizationStatus.ERROR,
            operating_mode=mode_classification.mode,
            operating_mode_reason=mode_classification.reason,
            horizon_start=inputs.horizon_start,
            horizon_end=actual_horizon_end,
            interval_minutes=inputs.interval_minutes,
            objective_value=solution.objective_value,
            recommended_battery_action=evaluation.battery_action,
            recommended_battery_power_w=evaluation.battery_power_w,
            load_recommendations=[
                {
                    "load_id": r.load_id,
                    "load_name": r.load_name,
                    "action": r.action,
                    "reason": r.reason,
                    "priority": r.priority,
                }
                for r in load_recs
            ],
            expected_grid_import_wh=evaluation.expected_grid_import_wh,
            expected_grid_export_wh=evaluation.expected_grid_export_wh,
            expected_renewable_utilization_pct=evaluation.expected_renewable_utilization_pct,
            expected_peak_w=evaluation.expected_peak_w,
            constraints_checked=[
                {"name": c.name, "satisfied": c.satisfied, "detail": c.detail} for c in evaluation.constraint_checks
            ],
            constraints_satisfied=evaluation.all_constraints_satisfied,
            explanation=explanation,
            recommendation_reason=reason,
            fallback_used=False,
            fallback_reason=None,
            provenance={
                "demand_forecast_model_id": str(inputs.demand_forecast.model_id)
                if inputs.demand_forecast.model_id
                else None,
                "solar_forecast_model_id": str(inputs.solar_forecast.model_id)
                if inputs.solar_forecast.model_id
                else None,
                "solver": "scipy.optimize.linprog (HiGHS)",
                "solve_time_ms": solution.solve_time_ms,
                "horizon_steps_used": n,
                "economic_optimization": "unavailable: no tariff data configured for this project",
            },
        )

        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)

        logger.info(
            "Decision optimization completed",
            extra={
                "context": {
                    "microgrid_id": str(microgrid_id),
                    "status": row.optimization_status.value,
                    "action": row.recommended_battery_action.value,
                    "solve_time_ms": solution.solve_time_ms,
                }
            },
        )
        return row

    def get_latest(self, microgrid_id: uuid.UUID) -> Optional[Decision]:
        self._require_microgrid(microgrid_id)
        return self.db.execute(
            select(Decision)
            .where(Decision.microgrid_id == microgrid_id)
            .order_by(Decision.created_at.desc())
            .limit(1)
        ).scalars().first()

    def list_history(self, microgrid_id: uuid.UUID, limit: int = 20) -> List[Decision]:
        self._require_microgrid(microgrid_id)
        return list(
            self.db.execute(
                select(Decision)
                .where(Decision.microgrid_id == microgrid_id)
                .order_by(Decision.created_at.desc())
                .limit(limit)
            ).scalars().all()
        )

    def set_approval(self, decision_id: uuid.UUID, approved: bool) -> Decision:
        """
        Records a human approval/rejection decision. This ONLY updates a
        database field — it never triggers any hardware action. See the
        module docstring and docs/architecture for the safety boundary.
        """
        row = self.db.get(Decision, decision_id)
        if row is None:
            raise NotFoundError(f"Decision {decision_id} not found.")
        row.approval_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        row.approved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    # --- internal helpers ---

    def _persist_fallback(self, inputs, reason: str) -> Decision:
        mode_classification = classify_operating_mode(
            evaluation=None,
            load_recommendations=[],
            current_soc_percent=inputs.current_battery_soc_percent,
            min_soc_percent=get_battery_constraints().min_soc_percent,
            emergency_buffer_percent=settings.DECISION_EMERGENCY_SOC_BUFFER_PERCENT,
            fallback_used=True,
        )
        row = Decision(
            microgrid_id=inputs.microgrid_id,
            source=inputs.source,
            optimization_status=OptimizationStatus.SAFE_FALLBACK,
            operating_mode=mode_classification.mode,
            operating_mode_reason=mode_classification.reason,
            horizon_start=inputs.horizon_start,
            horizon_end=inputs.horizon_end,
            interval_minutes=inputs.interval_minutes,
            objective_value=None,
            recommended_battery_action=BatteryAction.IDLE,
            recommended_battery_power_w=0.0,
            load_recommendations=[],
            expected_grid_import_wh=None,
            expected_grid_export_wh=None,
            expected_renewable_utilization_pct=None,
            expected_peak_w=None,
            constraints_checked=[],
            constraints_satisfied=False,
            explanation=f"No optimized recommendation was produced. Reason: {reason}",
            recommendation_reason="SAFE_FALLBACK: maintain current state, do not act on unoptimized data.",
            fallback_used=True,
            fallback_reason=reason,
            provenance={
                "demand_forecast_model_id": str(inputs.demand_forecast.model_id)
                if inputs.demand_forecast and inputs.demand_forecast.model_id
                else None,
                "solar_forecast_model_id": str(inputs.solar_forecast.model_id)
                if inputs.solar_forecast and inputs.solar_forecast.model_id
                else None,
                "solver": None,
                "solve_time_ms": 0.0,
                "economic_optimization": "unavailable: no tariff data configured for this project",
            },
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        logger.warning(
            "Decision fell back to SAFE_FALLBACK",
            extra={"context": {"microgrid_id": str(inputs.microgrid_id), "reason": reason}},
        )
        return row

    @staticmethod
    def _short_reason(evaluation) -> str:
        if evaluation.battery_action == BatteryAction.CHARGE:
            return "Charging recommended to capture forecasted generation without increasing grid import."
        if evaluation.battery_action == BatteryAction.DISCHARGE:
            return "Discharging recommended to reduce forecasted grid import while respecting minimum SOC."
        return "No battery action recommended under current forecasted conditions."

    def _require_microgrid(self, microgrid_id: uuid.UUID) -> Microgrid:
        microgrid = self.db.get(Microgrid, microgrid_id)
        if microgrid is None:
            raise NotFoundError(f"Microgrid {microgrid_id} not found.")
        return microgrid
