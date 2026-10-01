from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
DATA_DIR = BASE_DIR / "datasets" / "solar" / "processed"
MODEL_DIR = BASE_DIR / "ml" / "solar_forecasting" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

train = pd.read_csv(DATA_DIR / "solar_train.csv")
validation = pd.read_csv(DATA_DIR / "solar_validation.csv")
test = pd.read_csv(DATA_DIR / "solar_test.csv")

TARGET = "Active_Power"

DROP_COLUMNS = ["timestamp", TARGET]

FEATURES = [
    c for c in train.columns
    if c not in DROP_COLUMNS
]

X_train = train[FEATURES]
y_train = train[TARGET]

X_val = validation[FEATURES]
y_val = validation[TARGET]

X_test = test[FEATURES]
y_test = test[TARGET]


# ============================================================
# METRICS
# ============================================================

def smape(y_true, y_pred):

    denominator = np.abs(y_true) + np.abs(y_pred)

    mask = denominator != 0

    return (
        100
        * np.mean(
            2 * np.abs(y_pred[mask] - y_true[mask])
            / denominator[mask]
        )
    )


def evaluate(model, X, y):

    start = time.perf_counter()

    pred = model.predict(X)

    prediction_time = time.perf_counter() - start

    results = {
        "MAE_W": float(
            mean_absolute_error(y, pred) * 1000
        ),

        "RMSE_W": float(
            np.sqrt(
                mean_squared_error(y, pred)
            ) * 1000
        ),

        "SMAPE_percent": float(
            smape(y.values, pred)
        ),

        "R2": float(
            r2_score(y, pred)
        ),

        "prediction_time_seconds": prediction_time,
    }

    return results


# ============================================================
# INFORMATION
# ============================================================

print("=" * 70)
print("SOLAR XGBOOST")
print("=" * 70)

print(f"Features: {len(FEATURES)}")
print(f"Train: {len(X_train):,}")
print(f"Validation: {len(X_val):,}")
print(f"Test: {len(X_test):,}")


# ============================================================
# MODEL
# ============================================================

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


# ============================================================
# TRAIN
# ============================================================

print("\nTraining...")

start = time.perf_counter()

model.fit(
    X_train,
    y_train
)

training_time = time.perf_counter() - start

print(
    f"Training time: "
    f"{training_time:.2f} seconds"
)


# ============================================================
# VALIDATION
# ============================================================

print("\nEvaluating validation set...")

val_results = evaluate(
    model,
    X_val,
    y_val
)


print("\nVALIDATION RESULTS")
print("-" * 70)

for key, value in val_results.items():

    print(
        f"{key:30}: "
        f"{value:.6f}"
    )


# ============================================================
# TEST
# ============================================================

print("\nEvaluating test set...")

test_results = evaluate(
    model,
    X_test,
    y_test
)


print("\nTEST RESULTS")
print("-" * 70)

for key, value in test_results.items():

    print(
        f"{key:30}: "
        f"{value:.6f}"
    )


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

print("\nTOP FEATURES")
print("-" * 70)

importance = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(
    ascending=False
)

print(
    importance.head(15).to_string()
)


# ============================================================
# SAVE MODEL
# ============================================================

model_path = (
    MODEL_DIR
    / "solar_xgboost.joblib"
)

joblib.dump(
    model,
    model_path
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_path = (
    MODEL_DIR
    / "solar_xgboost_results.json"
)

results = {

    "model": "XGBRegressor",

    "n_estimators": 500,

    "max_depth": 8,

    "learning_rate": 0.05,

    "subsample": 0.8,

    "colsample_bytree": 0.8,

    "min_child_weight": 3,

    "random_state": 42,

    "feature_count": len(FEATURES),

    "train_rows": len(X_train),

    "validation_rows": len(X_val),

    "test_rows": len(X_test),

    "training_time_seconds":
        training_time,

    "validation": val_results,

    "test": test_results,

    "top_features":
        importance.head(15).to_dict(),
}


with open(
    results_path,
    "w"
) as f:

    json.dump(
        results,
        f,
        indent=2
    )


# ============================================================
# COMPLETE
# ============================================================

print("\nSaved model:")
print(model_path)

print("\nSaved results:")
print(results_path)

print("\n" + "=" * 70)
print("XGBOOST EXPERIMENT COMPLETE")
print("=" * 70)