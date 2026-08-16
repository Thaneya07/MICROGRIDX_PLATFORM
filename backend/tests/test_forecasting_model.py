import os
import tempfile

import pytest

from app.services.forecasting.model import ForecastModelWrapper


def _synthetic_data(n=100):
    X = [[i % 10, (i * 2) % 7, 0.0, 0.0, 0.0, 0.0, 0.0] for i in range(n)]
    y = [3 * row[0] - 2 * row[1] for row in X]
    return X, y


def test_predict_before_fit_raises():
    model = ForecastModelWrapper(random_state=1)
    with pytest.raises(RuntimeError):
        model.predict([[0, 0, 0, 0, 0, 0, 0]])


def test_fit_and_predict_learns_simple_relationship():
    X, y = _synthetic_data()
    model = ForecastModelWrapper(random_state=1)
    model.fit(X, y)
    preds = model.predict(X)
    errors = [abs(p - t) for p, t in zip(preds, y)]
    assert sum(errors) / len(errors) < 5.0


def test_predict_with_uncertainty_returns_valid_bounds():
    X, y = _synthetic_data()
    model = ForecastModelWrapper(random_state=1)
    model.fit(X, y)
    results = model.predict_with_uncertainty(X[:5])
    assert len(results) == 5
    for r in results:
        assert r.lower_95 <= r.mean <= r.upper_95
        assert r.lower_95 >= 0.0


def test_save_and_load_round_trip_produces_same_predictions():
    X, y = _synthetic_data()
    model = ForecastModelWrapper(random_state=1)
    model.fit(X, y)
    original_preds = model.predict(X[:10])

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "model.joblib")
        model.save(path)
        assert os.path.exists(path)

        loaded = ForecastModelWrapper.load(path, random_state=1)
        loaded_preds = loaded.predict(X[:10])

    assert original_preds == loaded_preds


def test_save_before_fit_raises():
    model = ForecastModelWrapper(random_state=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(RuntimeError):
            model.save(os.path.join(tmpdir, "model.joblib"))
