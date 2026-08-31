import pytest

from app.models.decision import BatteryAction
from app.services.decision.evaluator import ConstraintCheck, EvaluationResult
from app.services.decision.mode import classify_operating_mode
from app.services.decision.recommendations import LoadRecommendation
from app.services.decision_engine import OperatingMode


def _evaluation(action=BatteryAction.IDLE, satisfied=True, checks=None):
    return EvaluationResult(
        battery_action=action,
        battery_power_w=100.0,
        expected_grid_import_wh=0.0,
        expected_grid_export_wh=0.0,
        expected_renewable_utilization_pct=50.0,
        expected_peak_w=0.0,
        constraint_checks=checks or [ConstraintCheck("x", satisfied, "detail")],
        all_constraints_satisfied=satisfied,
    )


def test_fallback_used_is_always_emergency():
    result = classify_operating_mode(
        evaluation=None, load_recommendations=[], current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=True,
    )
    assert result.mode == OperatingMode.EMERGENCY_MODE
    assert "fallback" in result.reason.lower()


def test_violated_constraint_is_emergency_even_with_healthy_soc():
    evaluation = _evaluation(satisfied=False)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.EMERGENCY_MODE
    assert "constraint" in result.reason.lower()


def test_soc_at_emergency_threshold_is_emergency():
    evaluation = _evaluation(satisfied=True)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=24.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.EMERGENCY_MODE
    assert "soc" in result.reason.lower()


def test_soc_just_above_emergency_threshold_is_not_emergency():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.IDLE)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=26.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode != OperatingMode.EMERGENCY_MODE


def test_deferred_load_recommendation_is_eco():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.IDLE)
    deferred = [LoadRecommendation(load_id="1", load_name="EV Charger", action="DEFER", reason="x", priority=1)]
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=deferred, current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.ECO_MODE
    assert "EV Charger" in result.reason


def test_battery_discharge_with_no_deferrals_is_eco():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.DISCHARGE)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.ECO_MODE
    assert "discharge" in result.reason.lower()


def test_healthy_soc_no_deferral_no_discharge_is_normal():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.CHARGE)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.NORMAL_MODE


def test_healthy_soc_idle_battery_is_normal():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.IDLE)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=60.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.NORMAL_MODE


def test_priority_order_emergency_beats_eco_conditions():
    evaluation = _evaluation(satisfied=False, action=BatteryAction.DISCHARGE)
    deferred = [LoadRecommendation(load_id="1", load_name="X", action="DEFER", reason="x", priority=1)]
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=deferred, current_soc_percent=80.0,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.EMERGENCY_MODE


def test_unknown_soc_does_not_crash_and_does_not_force_emergency():
    evaluation = _evaluation(satisfied=True, action=BatteryAction.IDLE)
    result = classify_operating_mode(
        evaluation=evaluation, load_recommendations=[], current_soc_percent=None,
        min_soc_percent=20.0, emergency_buffer_percent=5.0, fallback_used=False,
    )
    assert result.mode == OperatingMode.NORMAL_MODE
