from pathlib import Path
import time
import json

import pandas as pd
import numpy as np

from xgboost import XGBRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

import joblib


# ============================================================
# MicroGridX - Demand Forecasting
# Step 6: XGBoost Experiment
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

TRAIN_PATH = DATA_DIR / "train.csv"
VAL_PATH = DATA_DIR / "validation.csv"
TEST_PATH = DATA_DIR / "test.csv"

MODEL_PATH = MODEL_DIR / "xgboost_demand_model.joblib"
RESULTS_PATH = MODEL_DIR / "xgboost_results.json"


print("=" * 70)
print("MicroGridX Demand Forecasting - XGBoost")
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
# Feature selection
# ------------------------------------------------------------

FEATURES = [
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

TARGET = "demand_w"


print("\nNumber of input features:", len(FEATURES))


# ------------------------------------------------------------
# Prepare X and y
# ------------------------------------------------------------

X_train = train[FEATURES]
y_train = train[TARGET]

X_val = validation[FEATURES]
y_val = validation[TARGET]

X_test = test[FEATURES]
y_test = test[TARGET]


# ------------------------------------------------------------
# Create XGBoost model
# ------------------------------------------------------------

model = XGBRegressor(
    n_estimators=500,
    max_depth=8,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    objective="reg:squarederror",
    eval_metric="rmse",
    random_state=42,
    n_jobs=-1,
    tree_method="hist",
)


# ------------------------------------------------------------
# Train
# ------------------------------------------------------------

print("\nTraining XGBoost...")

train_start = time.perf_counter()

model.fit(
    X_train,
    y_train,
    eval_set=[(X_val, y_val)],
    verbose=False,
)

train_time = time.perf_counter() - train_start

print(
    f"Training completed in {train_time:.2f} seconds"
)


# ------------------------------------------------------------
# Evaluation function
# ------------------------------------------------------------

def evaluate_model(model, X, y):

    start = time.perf_counter()

    predictions = model.predict(X)

    prediction_time = time.perf_counter() - start

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

    # SMAPE
    denominator = (
        np.abs(y)
        + np.abs(predictions)
    )

    non_zero = denominator != 0

    smape = np.mean(
        2
        * np.abs(
            predictions[non_zero]
            - y[non_zero]
        )
        / denominator[non_zero]
    ) * 100

    return {
        "MAE_W": float(mae),
        "RMSE_W": float(rmse),
        "SMAPE_percent": float(smape),
        "R2": float(r2),
        "prediction_time_seconds": float(
            prediction_time
        ),
    }, predictions


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

print("\nEvaluating validation set...")

validation_results, validation_predictions = (
    evaluate_model(
        model,
        X_val,
        y_val,
    )
)


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

print("Evaluating test set...")

test_results, test_predictions = evaluate_model(
    model,
    X_test,
    y_test,
)


# ------------------------------------------------------------
# Print validation results
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

for key, value in validation_results.items():
    print(
        f"{key:30}: {value:.6f}"
    )


# ------------------------------------------------------------
# Print test results
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL TEST RESULTS")
print("=" * 70)

for key, value in test_results.items():
    print(
        f"{key:30}: {value:.6f}"
    )


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
    ascending=False,
)


print("\n" + "=" * 70)
print("TOP FEATURE IMPORTANCE")
print("=" * 70)

print(
    importance
    .head(10)
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
# Save experiment results
# ------------------------------------------------------------

results = {
    "model": "XGBRegressor",

    "configuration": {
        "n_estimators": 500,
        "max_depth": 8,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "random_state": 42,
    },

    "features": FEATURES,

    "target": TARGET,

    "training_observations": len(train),

    "validation_observations": len(validation),

    "test_observations": len(test),

    "training_time_seconds": train_time,

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
    encoding="utf-8",
) as f:

    json.dump(
        results,
        f,
        indent=4,
    )


print("\nResults saved to:")
print(RESULTS_PATH)

print("\nXGBoost experiment complete.")