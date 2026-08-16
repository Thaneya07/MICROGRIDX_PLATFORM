from datetime import datetime, timedelta, timezone

from app.services.forecasting.baseline import fit_seasonal_naive_baseline


def test_baseline_predicts_historical_average_for_matching_hour():
    base = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)  # Monday
    timestamps = [base.replace(hour=8) + timedelta(days=d) for d in range(5)]  # weekdays, hour=8
    values = [100.0, 200.0, 300.0, 400.0, 500.0]
    baseline = fit_seasonal_naive_baseline(timestamps, values)
    pred = baseline.predict_one(datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc))
    assert pred == sum(values) / len(values)


def test_baseline_falls_back_to_overall_mean_for_unseen_bucket():
    timestamps = [datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc)]
    values = [100.0]
    baseline = fit_seasonal_naive_baseline(timestamps, values)
    pred = baseline.predict_one(datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc))
    assert pred == baseline.overall_mean


def test_baseline_distinguishes_weekday_and_weekend_for_same_hour():
    weekday = datetime(2026, 6, 15, 8, 0, tzinfo=timezone.utc)  # Monday
    weekend = datetime(2026, 6, 20, 8, 0, tzinfo=timezone.utc)  # Saturday
    timestamps = [weekday, weekend]
    values = [100.0, 900.0]
    baseline = fit_seasonal_naive_baseline(timestamps, values)
    assert baseline.predict_one(weekday) == 100.0
    assert baseline.predict_one(weekend) == 900.0


def test_baseline_predict_batch_matches_predict_one():
    timestamps = [datetime(2026, 6, 15, h, 0, tzinfo=timezone.utc) for h in range(24)]
    values = [float(h * 10) for h in range(24)]
    baseline = fit_seasonal_naive_baseline(timestamps, values)
    batch = baseline.predict(timestamps)
    individual = [baseline.predict_one(t) for t in timestamps]
    assert batch == individual
