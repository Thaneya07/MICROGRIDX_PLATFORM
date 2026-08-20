import pytest

from app.services.decision.constraints import BatteryConstraints
from app.services.decision.objective import ObjectiveWeights
from app.services.decision.optimizer import solve_dispatch

CONSTRAINTS = BatteryConstraints(
    capacity_wh=5000,
    min_soc_percent=20,
    max_soc_percent=95,
    max_charge_w=2000,
    max_discharge_w=2000,
    charge_efficiency=0.95,
    discharge_efficiency=0.95,
)
WEIGHTS = ObjectiveWeights(grid_import=1.0, grid_export=0.1, peak=0.5, degradation=0.05)


def test_high_solar_low_soc_recommends_charging():
    generation = [3000, 3500, 3800, 3000, 1000, 200, 0, 0]
    consumption = [400, 400, 400, 500, 600, 700, 800, 800]
    sol = solve_dispatch(generation, consumption, current_soc_wh=5000 * 0.30, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    assert sol.charge_w[0] > 0
    assert sol.discharge_w[0] == 0


def test_high_demand_low_solar_low_soc_avoids_discharge_to_protect_soc():
    generation = [0, 0, 0, 0, 0, 0, 0, 0]
    consumption = [900, 900, 900, 900, 900, 900, 900, 900]
    # SOC already at the configured minimum: optimizer must not discharge further.
    min_soc_wh = CONSTRAINTS.min_soc_wh
    sol = solve_dispatch(generation, consumption, current_soc_wh=min_soc_wh, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    assert sol.discharge_w[0] == pytest.approx(0.0, abs=1.0)
    for s in sol.soc_wh:
        assert s >= min_soc_wh - 1.0


def test_soc_never_exceeds_configured_maximum():
    generation = [4000] * 8
    consumption = [100] * 8
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.max_soc_wh - 10, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    for s in sol.soc_wh:
        assert s <= CONSTRAINTS.max_soc_wh + 1.0


def test_soc_never_drops_below_configured_minimum():
    generation = [0] * 8
    consumption = [2000] * 8
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.min_soc_wh + 50, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    for s in sol.soc_wh:
        assert s >= CONSTRAINTS.min_soc_wh - 1.0


def test_charge_power_never_exceeds_limit():
    generation = [10000] * 8  # extreme oversupply
    consumption = [0] * 8
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.min_soc_wh, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    for c in sol.charge_w:
        assert c <= CONSTRAINTS.max_charge_w + 1.0


def test_discharge_power_never_exceeds_limit():
    generation = [0] * 8
    consumption = [10000] * 8  # extreme demand spike
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.max_soc_wh, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    for d in sol.discharge_w:
        assert d <= CONSTRAINTS.max_discharge_w + 1.0


def test_no_simultaneous_charge_and_discharge_across_varied_scenarios():
    scenarios = [
        ([3000, 0, 3000, 0], [400, 900, 400, 900]),
        ([0, 500, 1000, 1500], [800, 800, 200, 200]),
        ([2000] * 4, [2000] * 4),
    ]
    for generation, consumption in scenarios:
        sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.capacity_wh * 0.5,
                              interval_minutes=30, constraints=CONSTRAINTS, weights=WEIGHTS)
        assert sol.success
        for c, d in zip(sol.charge_w, sol.discharge_w):
            assert not (c > 1.0 and d > 1.0), f"simultaneous charge={c} discharge={d}"


def test_energy_balance_holds_at_every_step():
    generation = [1500, 2000, 500, 0]
    consumption = [600, 400, 900, 700]
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.capacity_wh * 0.5, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    for t in range(len(generation)):
        supply = generation[t] + sol.discharge_w[t] + sol.grid_import_w[t]
        demand = consumption[t] + sol.charge_w[t] + sol.grid_export_w[t]
        assert supply == pytest.approx(demand, abs=0.5)


def test_result_is_deterministic_for_identical_inputs():
    generation = [1200, 800, 400, 0]
    consumption = [500, 600, 700, 800]
    sol1 = solve_dispatch(generation, consumption, current_soc_wh=2500, interval_minutes=30,
                           constraints=CONSTRAINTS, weights=WEIGHTS)
    sol2 = solve_dispatch(generation, consumption, current_soc_wh=2500, interval_minutes=30,
                           constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol1.charge_w == sol2.charge_w
    assert sol1.discharge_w == sol2.discharge_w
    assert sol1.objective_value == pytest.approx(sol2.objective_value, abs=1e-6)


def test_empty_horizon_reports_failure_not_a_fabricated_result():
    sol = solve_dispatch([], [], current_soc_wh=2500, interval_minutes=30, constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success is False
    assert sol.charge_w == []


def test_mismatched_series_lengths_reports_failure():
    sol = solve_dispatch([100, 200], [100], current_soc_wh=2500, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success is False


def test_peak_variable_tracks_maximum_grid_import():
    generation = [0, 0, 0, 0]
    consumption = [500, 900, 300, 700]
    sol = solve_dispatch(generation, consumption, current_soc_wh=CONSTRAINTS.min_soc_wh, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    assert sol.peak_w >= max(sol.grid_import_w) - 0.5


def test_solve_time_is_measured_and_fast():
    generation = [1000] * 8
    consumption = [500] * 8
    sol = solve_dispatch(generation, consumption, current_soc_wh=2500, interval_minutes=30,
                          constraints=CONSTRAINTS, weights=WEIGHTS)
    assert sol.success
    assert sol.solve_time_ms > 0
    assert sol.solve_time_ms < 1000  # measured, not merely asserted "real-time"
