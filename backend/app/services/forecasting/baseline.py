"""
Seasonal-naive baseline.

Predicts a timestamp's value as the historical average for that
(hour-of-day, is_weekend) bucket, computed from the training set. This is
the "simple statistical baseline" every trained model is compared against
(see forecasting/service.py) — if the trained model does not beat this on
held-out data, the service reports that honestly rather than serving a
model that adds no value over a lookup table.
"""
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SeasonalNaiveBaseline:
    bucket_means: Dict[Tuple[int, bool], float]
    overall_mean: float

    def predict_one(self, at: datetime) -> float:
        key = (at.hour, at.weekday() >= 5)
        return self.bucket_means.get(key, self.overall_mean)

    def predict(self, timestamps: List[datetime]) -> List[float]:
        return [self.predict_one(t) for t in timestamps]


def fit_seasonal_naive_baseline(timestamps: List[datetime], values: List[float]) -> SeasonalNaiveBaseline:
    buckets: Dict[Tuple[int, bool], List[float]] = {}
    for t, v in zip(timestamps, values):
        key = (t.hour, t.weekday() >= 5)
        buckets.setdefault(key, []).append(v)

    bucket_means = {key: statistics.fmean(vals) for key, vals in buckets.items()}
    overall_mean = statistics.fmean(values) if values else 0.0
    return SeasonalNaiveBaseline(bucket_means=bucket_means, overall_mean=overall_mean)
