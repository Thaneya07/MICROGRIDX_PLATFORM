from pathlib import Path
import time
import json

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

import joblib


# ============================================================
# MicroGridX - Demand Forecasting
# Step 9: Enhanced Random Forest
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
)

MODEL_DIR = (
    BASE_DIR
    / "ml"
    / "demand_forecasting"
    / "models"
)

MODEL_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_PATH = DATA_DIR / "enhanced_train.csv"
VAL_PATH = DATA_DIR / "enhanced_validation.csv"
TEST_PATH = DATA_DIR / "enhanced_test.csv"

MODEL_PATH = (
    MODEL_DIR
    / "enhanced_random_forest.joblib"
)

RESULTS_PATH = (
    MODEL_DIR
    / "enhanced_random_forest_results.json"
)


print("=" * 70)
print("MicroGridX Demand Forecasting - Enhanced Random Forest")
print("=" * 70)


# ------------------------------------------------------------
# Load datasets
# ------------------------------------------------------------

print("\nLoading datasets...")

train = pd.read_csv(TRAIN_PATH)
validation = pd.read_csv(VAL_PATH)
test = pd.read_csv(TEST_PATH)

for df in [train, validation, test]:
    df["timestamp"] = pd.to_datetime(df["timestamp"])


print(f"Training   : {len(train):,}")
print(f"Validation : {len(validation):,}")
print(f"Test       : {len(test):,}")


# ------------------------------------------------------------
# Features
# ------------------------------------------------------------

FEATURES = [
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

print("\nNumber of input features:", len(FEATURES))


# ------------------------------------------------------------
# Prepare data
# ------------------------------------------------------------

X_train = train[FEATURES]
y_train = train[TARGET]

X_val = validation[FEATURES]
y_val = validation[TARGET]

X_test = test[FEATURES]
y_test = test[TARGET]


# ------------------------------------------------------------
# Random Forest
# ------------------------------------------------------------

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
)


# ------------------------------------------------------------
# Train
# ------------------------------------------------------------

print("\nTraining Enhanced Random Forest...")

start_time = time.perf_counter()

model.fit(
    X_train,
    y_train
)

training_time = (
    time.perf_counter() - start_time
)

print(
    f"Training completed in "
    f"{training_time:.2f} seconds"
)


# ------------------------------------------------------------
# Evaluation
# ------------------------------------------------------------

def evaluate_model(model, X, y):

    start = time.perf_counter()

    predictions = model.predict(X)

    prediction_time = (
        time.perf_counter() - start
    )

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
            predictions[valid]
            - y[valid]
        )
        / denominator[valid]
    ) * 100

    return {
        "MAE_W": float(mae),
        "RMSE_W": float(rmse),
        "SMAPE_percent": float(smape),
        "R2": float(r2),
        "prediction_time_seconds": float(
            prediction_time
        ),
    }


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print("\nEvaluating validation set...")

validation_results = evaluate_model(
    model,
    X_val,
    y_val
)


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

print("Evaluating test set...")

test_results = evaluate_model(
    model,
    X_test,
    y_test
)


# ------------------------------------------------------------
# Print results
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

for key, value in validation_results.items():
    print(f"{key:30}: {value:.6f}")


print("\n" + "=" * 70)
print("FINAL TEST RESULTS")
print("=" * 70)

for key, value in test_results.items():
    print(f"{key:30}: {value:.6f}")


# ------------------------------------------------------------
# Feature importance
# ------------------------------------------------------------

importance = pd.DataFrame(
    {
        "feature": FEATURES,
        "importance": model.feature_importances_,
    }
).sort_values(
    "importance",
    ascending=False
)

print("\n" + "=" * 70)
print("TOP FEATURE IMPORTANCE")
print("=" * 70)

print(
    importance.head(15)
    .to_string(index=False)
)


# ------------------------------------------------------------
# Save model
# ------------------------------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)

print("\nModel saved to:")
print(MODEL_PATH)


# ------------------------------------------------------------
# Save results
# ------------------------------------------------------------

results = {
    "model": "Enhanced RandomForestRegressor",

    "configuration": {
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_leaf": 2,
        "random_state": 42,
    },

    "features": FEATURES,

    "target": TARGET,

    "training_observations": len(train),
    "validation_observations": len(validation),
    "test_observations": len(test),

    "training_time_seconds": training_time,

    "validation": validation_results,

    "test": test_results,

    "feature_importance": [
        {
            "feature": row["feature"],
            "importance": float(
                row["importance"]
            ),
        }
        for _, row in importance.iterrows()
    ],
}


with open(
    RESULTS_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=4
    )


print("\nResults saved to:")
print(RESULTS_PATH)

print("\nEnhanced Random Forest experiment complete.")