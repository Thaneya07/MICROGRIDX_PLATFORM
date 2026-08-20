"""
Battery/grid dispatch optimizer.

ALGORITHM SELECTION (documented rationale):

This is a small (n_steps ~= 4-16 decision points), linearly-structured
scheduling problem: power balance is linear, the battery SOC recursion is
linear, and every safety limit (SOC bounds, charge/discharge power caps)
is a linear bound or inequality. A Linear Program is the natural fit and
was chosen over:

  - MILP (mixed-integer, e.g. a binary "charging vs discharging" flag):
    not needed here. Simultaneous nonzero charge and discharge is made
    strictly wasteful by round-trip efficiency losses in the objective
    (see objective.py) — the LP relaxation naturally drives one of the
    two to zero at the optimum without integer variables. This keeps the
    problem solvable with a fast, deterministic simplex/interior-point
    method (scipy's HiGHS backend) instead of a combinatorial solver.
  - Quadratic Programming: no term in the objective is quadratic (no
    quadratic degradation model, no tariff-squared term); introducing one
    would add complexity with no basis in available data.
  - Model Predictive Control (as a wrapper): the horizon-based LP here
    already re-solves from the latest telemetry/forecast each time it's
    called (see service.py), which is the essence of MPC's receding
    horizon — a full MPC framework would add state/infrastructure this
    project's scale doesn't need yet.
  - A black-box/ML optimizer: would sacrifice explainability and
    guaranteed constraint satisfaction for no accuracy benefit on a
    problem this small and this linear.

scipy.optimize.linprog (method="highs") was chosen over adding OR-Tools
or PuLP as a new dependency: scipy is already a transitive dependency of
scikit-learn (used by Step 5 forecasting), so this introduces no new
package, and HiGHS is a modern, reliable, actively-maintained LP solver.

FORMULATION

Per horizon step t = 0..n-1 (n = n_steps), decision variables:
    charge_t        >= 0   (W, power into the battery)
    discharge_t      >= 0   (W, power out of the battery)
    grid_import_t    >= 0   (W)
    grid_export_t    >= 0   (W)
plus SOC state soc_0..soc_n (Wh, n+1 values; soc_0 fixed to the current
reading) and a single `peak` variable (W) used to linearize peak-shaving.

Power balance (equality) at each step:
    generation_t + discharge_t + grid_import_t
        = consumption_t + charge_t + grid_export_t

SOC recursion (equality):
    soc_{t+1} = soc_t + charge_t * dt_hours * eta_charge
                       - discharge_t * dt_hours / eta_discharge

Peak linearization (inequality), for each t:
    grid_import_t <= peak

Bounds: charge/discharge capped by configured max power; soc_t in
[min_soc_wh, max_soc_wh] for t >= 1; soc_0 fixed to the current reading.

Objective: see objective.py.
"""
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy.optimize import linprog

from app.services.decision.constraints import BatteryConstraints
from app.services.decision.objective import ObjectiveWeights


@dataclass(frozen=True)
class OptimizerSolution:
    success: bool
    status_message: str
    objective_value: Optional[float]
    charge_w: List[float]
    discharge_w: List[float]
    grid_import_w: List[float]
    grid_export_w: List[float]
    soc_wh: List[float]  # length n+1
    peak_w: Optional[float]
    solve_time_ms: float


def solve_dispatch(
    generation_w: List[float],
    consumption_w: List[float],
    current_soc_wh: float,
    interval_minutes: int,
    constraints: BatteryConstraints,
    weights: ObjectiveWeights,
) -> OptimizerSolution:
    n = len(generation_w)
    if n == 0 or len(consumption_w) != n:
        return OptimizerSolution(
            success=False,
            status_message="No forecast horizon to optimize over.",
            objective_value=None,
            charge_w=[],
            discharge_w=[],
            grid_import_w=[],
            grid_export_w=[],
            soc_wh=[],
            peak_w=None,
            solve_time_ms=0.0,
        )

    dt_hours = interval_minutes / 60.0
    n_vars = 4 * n + (n + 1) + 1  # charge, discharge, import, export, soc(n+1), peak

    def idx_charge(t):
        return t

    def idx_discharge(t):
        return n + t

    def idx_import(t):
        return 2 * n + t

    def idx_export(t):
        return 3 * n + t

    def idx_soc(t):
        return 4 * n + t

    idx_peak = 4 * n + (n + 1)

    # --- objective ---
    c = np.zeros(n_vars)
    for t in range(n):
        c[idx_charge(t)] += weights.degradation * dt_hours
        c[idx_discharge(t)] += weights.degradation * dt_hours
        c[idx_import(t)] += weights.grid_import * dt_hours
        c[idx_export(t)] += weights.grid_export * dt_hours
    c[idx_peak] += weights.peak

    # --- equality constraints ---
    A_eq = []
    b_eq = []

    for t in range(n):
        row = np.zeros(n_vars)
        row[idx_discharge(t)] = 1.0
        row[idx_import(t)] = 1.0
        row[idx_charge(t)] = -1.0
        row[idx_export(t)] = -1.0
        A_eq.append(row)
        b_eq.append(consumption_w[t] - generation_w[t])

    for t in range(n):
        row = np.zeros(n_vars)
        row[idx_soc(t + 1)] = 1.0
        row[idx_soc(t)] = -1.0
        row[idx_charge(t)] = -dt_hours * constraints.charge_efficiency
        row[idx_discharge(t)] = dt_hours / constraints.discharge_efficiency
        A_eq.append(row)
        b_eq.append(0.0)

    # --- inequality constraints (peak linearization) ---
    A_ub = []
    b_ub = []
    for t in range(n):
        row = np.zeros(n_vars)
        row[idx_import(t)] = 1.0
        row[idx_peak] = -1.0
        A_ub.append(row)
        b_ub.append(0.0)

    # --- bounds ---
    bounds = [(0.0, None)] * n_vars
    for t in range(n):
        bounds[idx_charge(t)] = (0.0, constraints.max_charge_w)
        bounds[idx_discharge(t)] = (0.0, constraints.max_discharge_w)
    bounds[idx_soc(0)] = (current_soc_wh, current_soc_wh)
    for t in range(1, n + 1):
        bounds[idx_soc(t)] = (constraints.min_soc_wh, constraints.max_soc_wh)
    bounds[idx_peak] = (0.0, None)

    start = time.perf_counter()
    result = linprog(
        c,
        A_ub=np.array(A_ub) if A_ub else None,
        b_ub=np.array(b_ub) if b_ub else None,
        A_eq=np.array(A_eq),
        b_eq=np.array(b_eq),
        bounds=bounds,
        method="highs",
    )
    solve_time_ms = (time.perf_counter() - start) * 1000.0

    if not result.success:
        return OptimizerSolution(
            success=False,
            status_message=result.message,
            objective_value=None,
            charge_w=[],
            discharge_w=[],
            grid_import_w=[],
            grid_export_w=[],
            soc_wh=[],
            peak_w=None,
            solve_time_ms=solve_time_ms,
        )

    x = result.x
    return OptimizerSolution(
        success=True,
        status_message=result.message,
        objective_value=float(result.fun),
        charge_w=[float(x[idx_charge(t)]) for t in range(n)],
        discharge_w=[float(x[idx_discharge(t)]) for t in range(n)],
        grid_import_w=[float(x[idx_import(t)]) for t in range(n)],
        grid_export_w=[float(x[idx_export(t)]) for t in range(n)],
        soc_wh=[float(x[idx_soc(t)]) for t in range(n + 1)],
        peak_w=float(x[idx_peak]),
        solve_time_ms=solve_time_ms,
    )
