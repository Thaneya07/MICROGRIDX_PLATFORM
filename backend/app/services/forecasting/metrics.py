"""
Forecast evaluation metrics.

Plain, dependency-light implementations (no sklearn.metrics import here,
so this module has no hidden coupling to the chosen model library) used to
score both the trained model and the baseline on held-out data. Every
number returned is computed directly from the (y_true, y_pred) arrays
passed in — there is no path in this module that returns a fabricated or
default metric value.
"""
import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class RegressionMetrics:
    mae: float
    rmse: float
    smape: Optional[float]  # undefined (None) when all true+pred pairs are exactly zero
    r2: Optional[float]  # undefined (None) when y_true has zero variance
    n: int


def compute_regression_metrics(y_true: List[float], y_pred: List[float]) -> RegressionMetrics:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length.")
    n = len(y_true)
    if n == 0:
        raise ValueError("Cannot compute metrics on an empty set.")

    errors = [yt - yp for yt, yp in zip(y_true, y_pred)]
    abs_errors = [abs(e) for e in errors]
    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(e * e for e in errors) / n)

    smape_terms = []
    for yt, yp in zip(y_true, y_pred):
        denom = abs(yt) + abs(yp)
        if denom > 0:
            smape_terms.append(abs(yt - yp) / denom)
    smape = (sum(smape_terms) / len(smape_terms) * 100.0) if smape_terms else None

    mean_y_true = sum(y_true) / n
    ss_tot = sum((yt - mean_y_true) ** 2 for yt in y_true)
    if ss_tot > 0:
        ss_res = sum(e * e for e in errors)
        r2 = 1.0 - (ss_res / ss_tot)
    else:
        r2 = None

    return RegressionMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        smape=round(smape, 4) if smape is not None else None,
        r2=round(r2, 4) if r2 is not None else None,
        n=n,
    )
