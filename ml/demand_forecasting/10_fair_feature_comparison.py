from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


# ============================================================
# MicroGridX - Demand Forecasting
# Step 10: Fair Feature-Ablation Comparison
#
# Both models are evaluated on EXACTLY the same timestamps.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
)

TRAIN_PATH = DATA_DIR / "enhanced_train.csv"
VAL_PATH = DATA_DIR / "enhanced_validation.csv"
TEST_PATH = DATA_DIR / "enhanced_test.csv"


print("=" * 70)
print("MicroGridX - Fair Feature Comparison")
print("=" * 70)


# ------------------------------------------------------------
# Load enhanced splits
# ------------------------------------------------------------

train = pd.read_csv(TRAIN_PATH)
validation = pd.read_csv(VAL_PATH)
test = pd.read_csv(TEST_PATH)

for df in [train, validation, test]:
    df["timestamp"] = pd.to_datetime(df["timestamp"])


print("\nEnhanced split sizes:")
print(f"Training   : {len(train):,}")
print(f"Validation : {len(validation):,}")
print(f"Test       : {len(test):,}")


# ------------------------------------------------------------
# Feature sets
# ------------------------------------------------------------

BASELINE_FEATURES = [
    "demand_lag_1",
    "demand_lag_2",
    "demand_lag_3",
    "demand_lag_48",
    "demand_lag_96",

    "demand_rolling_mean_3",
    "demand_rolling_std_3",
    "demand_rolling_mean_6",
    "demand_rolling_mean_48",
    "demand_rolling_max_48",
    "demand_rolling_min_48",

    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]


ENHANCED_FEATURES = [
    "demand_lag_1",
    "demand_lag_2",
    "demand_lag_3",
    "demand_lag_48",
    "demand_lag_96",
    "demand_lag_336",

    "demand_rolling_mean_3",
    "demand_rolling_std_3",
    "demand_rolling_mean_6",
    "demand_rolling_std_6",

    "demand_rolling_mean_48",
    "demand_rolling_std_48",
    "demand_rolling_max_48",
    "demand_rolling_min_48",

    "demand_rolling_mean_336",
    "demand_rolling_std_336",

    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]


TARGET = "demand_w"


# ------------------------------------------------------------
# Evaluation function
# ------------------------------------------------------------

def evaluate(model, X, y):

    predictions = model.predict(X)

    mae = mean_absolute_error(
        y,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y,
            predictions
        )
    )

    r2 = r2_score(
        y,
        predictions
    )

    denominator = (
        np.abs(y)
        + np.abs(predictions)
    )

    valid = denominator != 0

    smape = np.mean(
        2
        * np.abs(
            predictions[valid] - y[valid]
        )
        / denominator[valid]
    ) * 100

    return {
        "MAE_W": mae,
        "RMSE_W": rmse,
        "SMAPE_percent": smape,
        "R2": r2,
    }


# ------------------------------------------------------------
# Train function
# ------------------------------------------------------------

def train_and_evaluate(
    name,
    features,
):

    print("\n" + "-" * 70)
    print(f"Training: {name}")
    print("-" * 70)

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        train[features],
        train[TARGET]
    )

    validation_results = evaluate(
        model,
        validation[features],
        validation[TARGET],
    )

    test_results = evaluate(
        model,
        test[features],
        test[TARGET],
    )

    return (
        model,
        validation_results,
        test_results,
    )


# ------------------------------------------------------------
# Train baseline
# ------------------------------------------------------------

(
    baseline_model,
    baseline_validation,
    baseline_test,
) = train_and_evaluate(
    "Original 18-Feature Random Forest",
    BASELINE_FEATURES,
)


# ------------------------------------------------------------
# Train enhanced model
# ------------------------------------------------------------

(
    enhanced_model,
    enhanced_validation,
    enhanced_test,
) = train_and_evaluate(
    "Enhanced 23-Feature Random Forest",
    ENHANCED_FEATURES,
)


# ------------------------------------------------------------
# Print validation comparison
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDATION COMPARISON")
print("=" * 70)

print(
    f"{'Metric':<20}"
    f"{'Baseline':>15}"
    f"{'Enhanced':>15}"
)

print("-" * 50)

for metric in [
    "MAE_W",
    "RMSE_W",
    "SMAPE_percent",
    "R2",
]:

    print(
        f"{metric:<20}"
        f"{baseline_validation[metric]:>15.4f}"
        f"{enhanced_validation[metric]:>15.4f}"
    )


# ------------------------------------------------------------
# Print test comparison
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("TEST COMPARISON")
print("=" * 70)

print(
    f"{'Metric':<20}"
    f"{'Baseline':>15}"
    f"{'Enhanced':>15}"
    f"{'Difference':>15}"
)

print("-" * 65)

for metric in [
    "MAE_W",
    "RMSE_W",
    "SMAPE_percent",
    "R2",
]:

    baseline_value = baseline_test[metric]
    enhanced_value = enhanced_test[metric]

    difference = (
        enhanced_value - baseline_value
    )

    print(
        f"{metric:<20}"
        f"{baseline_value:>15.4f}"
        f"{enhanced_value:>15.4f}"
        f"{difference:>15.4f}"
    )


# ------------------------------------------------------------
# Calculate percentage changes
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("TEST METRIC CHANGE")
print("=" * 70)

for metric in [
    "MAE_W",
    "RMSE_W",
    "SMAPE_percent",
    "R2",
]:

    baseline_value = baseline_test[metric]
    enhanced_value = enhanced_test[metric]

    percentage_change = (
        (enhanced_value - baseline_value)
        / abs(baseline_value)
    ) * 100

    print(
        f"{metric:<20}: "
        f"{percentage_change:+.4f}%"
    )


# ------------------------------------------------------------
# Final statement
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("FAIR COMPARISON COMPLETE")
print("=" * 70)

print(
    "\nBoth models were evaluated using "
    "the exact same train, validation, and test timestamps."
)

print(
    "No test-set tuning was performed."
)