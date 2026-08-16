import pytest

from app.services.forecasting.metrics import compute_regression_metrics


def test_perfect_predictions_give_zero_error_and_r2_one():
    y_true = [10.0, 20.0, 30.0]
    y_pred = [10.0, 20.0, 30.0]
    m = compute_regression_metrics(y_true, y_pred)
    assert m.mae == 0.0
    assert m.rmse == 0.0
    assert m.smape == 0.0
    assert m.r2 == 1.0


def test_mae_and_rmse_known_values():
    y_true = [0.0, 0.0, 0.0]
    y_pred = [1.0, -1.0, 2.0]
    m = compute_regression_metrics(y_true, y_pred)
    assert m.mae == pytest.approx(4.0 / 3.0, abs=1e-3)
    assert m.rmse == pytest.approx((6.0 / 3.0) ** 0.5, abs=1e-3)


def test_r2_none_when_true_values_have_zero_variance():
    y_true = [5.0, 5.0, 5.0]
    y_pred = [4.0, 5.0, 6.0]
    m = compute_regression_metrics(y_true, y_pred)
    assert m.r2 is None


def test_smape_none_when_all_pairs_are_zero():
    y_true = [0.0, 0.0]
    y_pred = [0.0, 0.0]
    m = compute_regression_metrics(y_true, y_pred)
    assert m.smape is None
    assert m.mae == 0.0


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        compute_regression_metrics([1.0, 2.0], [1.0])


def test_empty_input_raises():
    with pytest.raises(ValueError):
        compute_regression_metrics([], [])


def test_worse_predictions_never_produce_negative_mae_rmse():
    y_true = [100.0, 200.0, 50.0]
    y_pred = [10.0, 900.0, -20.0]
    m = compute_regression_metrics(y_true, y_pred)
    assert m.mae >= 0
    assert m.rmse >= 0
