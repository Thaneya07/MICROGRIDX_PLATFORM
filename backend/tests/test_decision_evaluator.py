import pytest

from app.models.decision import BatteryAction
from app.services.decision.constraints import BatteryConstraints
from app.services.decision.evaluator import check_constraints, evaluate_solution
from app.services.decision.optimizer import OptimizerSolution

CONSTRAINTS = BatteryConstraints(
    capacity_wh=5000, min_soc_percent=20, max_soc_percent=95,
    max_charge_w=2000, max_discharge_w=2000,
    charge_efficiency=0.95, discharge_efficiency=0.95,
)


def _solution(**overrides):
    defaults = dict(
        success=True,
        status_message="ok",
        objective_value=10.0,
        charge_w=[500.0, 0.0],
        discharge_w=[0.0, 300.0],
        grid_import_w=[0.0, 0.0],
        grid_export_w=[0.0, 0.0],
        soc_wh=[2500.0, 2900.0, 2600.0],
        peak_w=100.0,
        solve_time_ms=5.0,
    )
    defaults.update(overrides)
    return OptimizerSolution(**defaults)


def test_check_constraints_all_satisfied_for_valid_solution():
    checks = check_constraints(_solution(), CONSTRAINTS)
    assert all(c.satisfied for c in checks)


def test_check_constraints_detects_soc_below_minimum():
    sol = _solution(soc_wh=[2500.0, 500.0, 600.0])  # below min_soc_wh (1000)
    checks = check_constraints(sol, CONSTRAINTS)
    soc_check = next(c for c in checks if c.name == "battery_soc_within_bounds")
    assert soc_check.satisfied is False


def test_check_constraints_detects_soc_above_maximum():
    sol = _solution(soc_wh=[2500.0, 4900.0, 4950.0])  # above max_soc_wh (4750)
    checks = check_constraints(sol, CONSTRAINTS)
    soc_check = next(c for c in checks if c.name == "battery_soc_within_bounds")
    assert soc_check.satisfied is False


def test_check_constraints_detects_charge_power_violation():
    sol = _solution(charge_w=[2500.0, 0.0])  # exceeds max_charge_w (2000)
    checks = check_constraints(sol, CONSTRAINTS)
    check = next(c for c in checks if c.name == "charge_power_within_limit")
    assert check.satisfied is False


def test_check_constraints_detects_discharge_power_violation():
    sol = _solution(discharge_w=[0.0, 2500.0])
    checks = check_constraints(sol, CONSTRAINTS)
    check = next(c for c in checks if c.name == "discharge_power_within_limit")
    assert check.satisfied is False


def test_check_constraints_detects_simultaneous_charge_discharge():
    sol = _solution(charge_w=[500.0, 500.0], discharge_w=[500.0, 0.0])
    checks = check_constraints(sol, CONSTRAINTS)
    check = next(c for c in checks if c.name == "no_simultaneous_charge_discharge")
    assert check.satisfied is False


def test_evaluate_solution_classifies_charge_action():
    result = evaluate_solution(_solution(), CONSTRAINTS, interval_minutes=30, total_consumption_wh=1000.0)
    assert result.battery_action == BatteryAction.CHARGE
    assert result.battery_power_w == 500.0


def test_evaluate_solution_classifies_idle_when_no_significant_flow():
    sol = _solution(charge_w=[0.0, 0.0], discharge_w=[0.0, 0.0])
    result = evaluate_solution(sol, CONSTRAINTS, interval_minutes=30, total_consumption_wh=1000.0)
    assert result.battery_action == BatteryAction.IDLE
    assert result.battery_power_w == 0.0


def test_evaluate_solution_computes_renewable_utilization_pct():
    sol = _solution(grid_import_w=[100.0, 100.0])
    result = evaluate_solution(sol, CONSTRAINTS, interval_minutes=60, total_consumption_wh=1000.0)
    # grid_import_wh = 100*1 + 100*1 = 200; self-consumed = 800; pct = 80
    assert result.expected_renewable_utilization_pct == pytest.approx(80.0, abs=0.1)


def test_evaluate_solution_flags_unsatisfied_constraints():
    sol = _solution(charge_w=[3000.0, 0.0])  # violates max_charge_w
    result = evaluate_solution(sol, CONSTRAINTS, interval_minutes=30, total_consumption_wh=1000.0)
    assert result.all_constraints_satisfied is False
