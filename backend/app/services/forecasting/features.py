"""
Feature preparation for forecasting.

Design decision (documented, not incidental): features are calendar-only
(hour-of-day, day-of-week, month, weekend flag — each cyclically encoded
where periodic) with no lag/rolling-window features.

Why: the only telemetry source available today is `SimulationTelemetryProvider`,
which by construction generates consumption/generation as a function of
time-of-day and day-of-week (see app/services/telemetry/simulation.py) —
the data-generating process has no meaningful short-term autocorrelation
beyond calendar effects. Lag features would add recursive-forecasting
complexity (each predicted step depends on the previous prediction, which
compounds error over the horizon) without evidence they would improve
accuracy on this data. This is exactly the kind of choice the model
should revisit once hardware telemetry (with real short-term
autocorrelation/noise structure) is available — noted in `docs/architecture`.

Cyclical encoding (sin/cos) is used instead of raw integers so the model
does not see a discontinuity between, e.g., hour 23 and hour 0.
"""
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List

FEATURE_NAMES: List[str] = [
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]


def _cyclical(value: float, period: float) -> tuple[float, float]:
    angle = 2 * math.pi * (value / period)
    return math.sin(angle), math.cos(angle)


def build_feature_vector(at: datetime) -> List[float]:
    """Build the calendar feature vector for a single timestamp, in FEATURE_NAMES order."""
    hour_frac = at.hour + at.minute / 60.0
    hour_sin, hour_cos = _cyclical(hour_frac, 24.0)
    dow_sin, dow_cos = _cyclical(float(at.weekday()), 7.0)
    month_sin, month_cos = _cyclical(float(at.month - 1), 12.0)
    is_weekend = 1.0 if at.weekday() >= 5 else 0.0
    return [hour_sin, hour_cos, dow_sin, dow_cos, month_sin, month_cos, is_weekend]


def build_feature_matrix(timestamps: List[datetime]) -> List[List[float]]:
    return [build_feature_vector(at) for at in timestamps]
