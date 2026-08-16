"""
Forecasting model.

Algorithm selection (documented rationale, evaluated against the criteria
in the Phase 2 spec — data availability, temporal characteristics,
horizon, accuracy, robustness, inference latency, model complexity,
deployment suitability):

  Chosen: RandomForestRegressor (scikit-learn), one per (microgrid, target).

  Why not deep sequence models (LSTM / Temporal Fusion Transformer /
  PatchTST): these need large volumes of historical data to avoid
  overfitting and add real deployment complexity (training infra, larger
  serialized artifacts). Telemetry volume at this stage is whatever has
  been persisted via /api/telemetry for a given microgrid — from zero up
  to at most a few months for the most actively-queried demo microgrids.
  That is well below the volume where sequence models reliably outperform
  tree ensembles on a feature set this simple.

  Why not gradient boosting (XGBoost/LightGBM): a bagged tree ensemble
  (Random Forest) was preferred over boosted trees for this first
  implementation because it is less prone to overfitting a small dataset
  with default hyperparameters (no boosting-round/learning-rate tuning
  required to get a reasonable result), and its per-tree prediction
  spread gives a natural, honest uncertainty estimate without a separate
  quantile-regression model. This is a deployment/complexity trade-off
  appropriate for the current data volume, revisitable once enough
  training history exists to tune boosting properly.

  Why not a plain linear/statistical model as the *served* model: the
  seasonal-naive baseline (baseline.py) already covers that role, and is
  used as the comparison floor — see ForecastingService.

Uncertainty: for a Random Forest, each of the `n_estimators` trees
produces an independent prediction; the spread across trees is a
reasonable (if approximate — not a calibrated interval) proxy for
predictive uncertainty, reported as a mean +/- ~1.96*std band. This is
presented as an approximation in every API response, never as a
statistically calibrated confidence interval.
"""
from dataclasses import dataclass
from typing import List

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor


@dataclass(frozen=True)
class PredictionWithUncertainty:
    mean: float
    lower_95: float
    upper_95: float


class ForecastModelWrapper:
    """Thin wrapper around a fitted RandomForestRegressor plus save/load."""

    ALGORITHM_NAME = "RandomForestRegressor"

    def __init__(self, random_state: int, n_estimators: int = 200, max_depth: int = 10):
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=-1,
        )
        self._fitted = False

    def fit(self, X: List[List[float]], y: List[float]) -> None:
        self._model.fit(np.array(X), np.array(y))
        self._fitted = True

    def predict(self, X: List[List[float]]) -> List[float]:
        self._require_fitted()
        return list(self._model.predict(np.array(X)))

    def predict_with_uncertainty(self, X: List[List[float]]) -> List[PredictionWithUncertainty]:
        self._require_fitted()
        X_arr = np.array(X)
        # Per-tree predictions: shape (n_estimators, n_samples)
        tree_predictions = np.array([tree.predict(X_arr) for tree in self._model.estimators_])
        means = tree_predictions.mean(axis=0)
        stds = tree_predictions.std(axis=0)
        results = []
        for mean, std in zip(means, stds):
            mean = float(mean)
            std = float(std)
            raw_lower = mean - 1.96 * std
            raw_upper = mean + 1.96 * std

            # Power/energy values cannot be negative. Clamp the mean itself
            # first, then derive bounds relative to the clamped mean so the
            # lower <= mean <= upper invariant holds even when the raw
            # (unclamped) mean is negative noise around zero.
            mean_clamped = max(0.0, mean)
            lower = max(0.0, min(raw_lower, mean_clamped))
            upper = max(raw_upper, mean_clamped)

            results.append(PredictionWithUncertainty(mean=mean_clamped, lower_95=lower, upper_95=upper))
        return results

    def save(self, path: str) -> None:
        self._require_fitted()
        joblib.dump(self._model, path)

    @classmethod
    def load(cls, path: str, random_state: int) -> "ForecastModelWrapper":
        wrapper = cls(random_state=random_state)
        wrapper._model = joblib.load(path)
        wrapper._fitted = True
        return wrapper

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError("ForecastModelWrapper.fit() must be called before predict().")
