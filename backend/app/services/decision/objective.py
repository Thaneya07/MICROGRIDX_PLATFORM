"""
Optimization objective weights.

minimize:
    w_grid_import  * sum(grid_import_t  * dt_hours)      -- energy imported from the grid
  + w_grid_export   * sum(grid_export_t  * dt_hours)      -- discourage unnecessary export/curtailment
  + w_peak          * peak_grid_import_w                  -- flatten the worst single-interval import
  + w_degradation   * sum((charge_t + discharge_t) * dt_hours)  -- proxy for battery cycling/throughput

No monetary/tariff term exists: this project has no tariff data source
(see app/services/decision/service.py — reported explicitly in every
decision's provenance as "economic_optimization: unavailable, no tariff
data configured"), so economic optimization is left out rather than
fabricated with invented prices.

Renewable self-consumption is not a separate weighted term: because the
power-balance equality constraint (see optimizer.py) forces
generation + discharge + grid_import = consumption + charge + grid_export,
minimizing grid_import already maximizes renewable self-consumption by
construction — adding a second term for the same effect would just be
double-counting the same physical quantity.
"""
from dataclasses import dataclass

from app.core.config import get_settings

settings = get_settings()


@dataclass(frozen=True)
class ObjectiveWeights:
    grid_import: float
    grid_export: float
    peak: float
    degradation: float


def get_objective_weights() -> ObjectiveWeights:
    return ObjectiveWeights(
        grid_import=settings.DECISION_WEIGHT_GRID_IMPORT,
        grid_export=settings.DECISION_WEIGHT_GRID_EXPORT,
        peak=settings.DECISION_WEIGHT_PEAK,
        degradation=settings.DECISION_WEIGHT_DEGRADATION,
    )
