import uuid

from app.models.decision import BatteryAction
from app.models.load import LoadCategory, LoadControlMode, LoadStatus
from app.services.decision.evaluator import EvaluationResult
from app.services.decision.recommendations import build_explanation, build_load_recommendations


class _FakeLoad:
    def __init__(self, name, priority, controllable, status):
        self.id = uuid.uuid4()
        self.name = name
        self.priority = priority
        self.controllable = controllable
        self.status = status
        self.category = LoadCategory.OTHER
        self.control_mode = LoadControlMode.AUTOMATIC


def _evaluation(**overrides):
    defaults = dict(
        battery_action=BatteryAction.DISCHARGE,
        battery_power_w=500.0,
        expected_grid_import_wh=200.0,
        expected_grid_export_wh=0.0,
        expected_renewable_utilization_pct=60.0,
        expected_peak_w=500.0,
        constraint_checks=[],
        all_constraints_satisfied=True,
    )
    defaults.update(overrides)
    return EvaluationResult(**defaults)


def test_defers_lowest_priority_controllable_on_loads_under_pressure():
    loads = [
        _FakeLoad("Fridge", priority=10, controllable=False, status=LoadStatus.ON),
        _FakeLoad("EV Charger", priority=1, controllable=True, status=LoadStatus.ON),
        _FakeLoad("Washing Machine", priority=3, controllable=True, status=LoadStatus.ON),
    ]
    evaluation = _evaluation(battery_action=BatteryAction.DISCHARGE, expected_peak_w=500.0)
    recs = build_load_recommendations(loads, evaluation)

    ev_rec = next(r for r in recs if r.load_name == "EV Charger")
    assert ev_rec.action == "DEFER"

    fridge_rec = next(r for r in recs if r.load_name == "Fridge")
    assert fridge_rec.action == "MAINTAIN"  # non-controllable, never touched


def test_recommends_run_now_for_off_loads_when_surplus_exists():
    loads = [
        _FakeLoad("Pool Pump", priority=2, controllable=True, status=LoadStatus.OFF),
    ]
    evaluation = _evaluation(
        battery_action=BatteryAction.CHARGE, expected_peak_w=0.0, expected_grid_export_wh=500.0
    )
    recs = build_load_recommendations(loads, evaluation)
    pump_rec = next(r for r in recs if r.load_name == "Pool Pump")
    assert pump_rec.action == "RUN_NOW"


def test_maintains_all_loads_when_no_pressure_or_surplus():
    loads = [_FakeLoad("Lights", priority=5, controllable=True, status=LoadStatus.ON)]
    evaluation = _evaluation(battery_action=BatteryAction.IDLE, expected_peak_w=0.0, expected_grid_export_wh=0.0)
    recs = build_load_recommendations(loads, evaluation)
    assert all(r.action == "MAINTAIN" for r in recs)


def test_every_load_gets_exactly_one_recommendation():
    loads = [
        _FakeLoad("A", priority=1, controllable=True, status=LoadStatus.ON),
        _FakeLoad("B", priority=2, controllable=True, status=LoadStatus.OFF),
        _FakeLoad("C", priority=3, controllable=False, status=LoadStatus.ON),
    ]
    evaluation = _evaluation(battery_action=BatteryAction.DISCHARGE, expected_peak_w=100.0)
    recs = build_load_recommendations(loads, evaluation)
    assert len(recs) == len(loads)
    assert {r.load_name for r in recs} == {"A", "B", "C"}


def test_explanation_reflects_charge_action_and_current_soc():
    evaluation = _evaluation(battery_action=BatteryAction.CHARGE, battery_power_w=800.0)
    explanation = build_explanation(evaluation, [500.0], [1000.0, 1500.0], current_soc_percent=40.0,
                                     constraints_max_soc=95.0, constraints_min_soc=20.0)
    assert "charging" in explanation.lower()
    assert "800" in explanation
    assert "40%" in explanation


def test_explanation_reflects_discharge_action():
    evaluation = _evaluation(battery_action=BatteryAction.DISCHARGE, battery_power_w=300.0,
                              expected_grid_import_wh=150.0)
    explanation = build_explanation(evaluation, [900.0], [0.0], current_soc_percent=70.0,
                                     constraints_max_soc=95.0, constraints_min_soc=20.0)
    assert "discharge" in explanation.lower()
    assert "300" in explanation


def test_explanation_reflects_idle_action():
    evaluation = _evaluation(battery_action=BatteryAction.IDLE, battery_power_w=0.0)
    explanation = build_explanation(evaluation, [500.0], [500.0], current_soc_percent=50.0,
                                     constraints_max_soc=95.0, constraints_min_soc=20.0)
    assert "no battery action" in explanation.lower()


def test_explanation_is_not_a_generic_template_it_varies_with_inputs():
    charge_evaluation = _evaluation(battery_action=BatteryAction.CHARGE, battery_power_w=100.0)
    discharge_evaluation = _evaluation(battery_action=BatteryAction.DISCHARGE, battery_power_w=100.0)
    charge_explanation = build_explanation(charge_evaluation, [1], [1], 50.0, 95.0, 20.0)
    discharge_explanation = build_explanation(discharge_evaluation, [1], [1], 50.0, 95.0, 20.0)
    assert charge_explanation != discharge_explanation
