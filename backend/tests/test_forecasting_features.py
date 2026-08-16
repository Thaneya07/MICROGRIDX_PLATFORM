import math
from datetime import datetime, timezone

from app.services.forecasting.features import FEATURE_NAMES, build_feature_matrix, build_feature_vector


def test_feature_vector_has_expected_length_and_order():
    at = datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc)
    vec = build_feature_vector(at)
    assert len(vec) == len(FEATURE_NAMES) == 7


def test_hour_cyclical_encoding_wraps_correctly():
    midnight = build_feature_vector(datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc))
    almost_midnight = build_feature_vector(datetime(2026, 6, 15, 23, 59, tzinfo=timezone.utc))
    # hour_sin/hour_cos should be close for times near the day boundary
    # (that's the whole point of cyclical encoding).
    assert abs(midnight[0] - almost_midnight[0]) < 0.05
    assert abs(midnight[1] - almost_midnight[1]) < 0.05


def test_noon_and_midnight_are_maximally_different_in_hour_encoding():
    midnight = build_feature_vector(datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc))
    noon = build_feature_vector(datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc))
    # cos(0) - cos(pi) = 1 - (-1) = 2, the maximum possible difference
    assert abs(midnight[1] - noon[1]) > 1.9


def test_weekend_flag_correct():
    saturday = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)  # Saturday
    monday = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)  # Monday
    assert build_feature_vector(saturday)[6] == 1.0
    assert build_feature_vector(monday)[6] == 0.0


def test_feature_matrix_matches_input_length():
    timestamps = [datetime(2026, 6, 15, h, 0, tzinfo=timezone.utc) for h in range(5)]
    matrix = build_feature_matrix(timestamps)
    assert len(matrix) == 5
    assert all(len(row) == len(FEATURE_NAMES) for row in matrix)


def test_all_cyclical_values_within_unit_circle():
    for h in range(24):
        vec = build_feature_vector(datetime(2026, 6, 15, h, 0, tzinfo=timezone.utc))
        for v in vec[:6]:  # sin/cos features only, not the weekend flag
            assert -1.0 <= v <= 1.0
