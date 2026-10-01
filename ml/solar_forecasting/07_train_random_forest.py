from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
DATA_DIR = BASE_DIR / "datasets" / "solar" / "processed"
MODEL_DIR = BASE_DIR / "ml" / "solar_forecasting" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

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
    pred = model.predict(X)

    return {
        "MAE_W": float(mean_absolute_error(y, pred) * 1000),
        "RMSE_W": float(
            np.sqrt(mean_squared_error(y, pred)) * 1000
        ),
        "SMAPE_percent": float(smape(y.values, pred)),
        "R2": float(r2_score(y, pred)),
    }


print("=" * 70)
print("SOLAR RANDOM FOREST BASELINE")
print("=" * 70)

print(f"Features: {len(FEATURES)}")
print(f"Train: {len(X_train):,}")
print(f"Validation: {len(X_val):,}")
print(f"Test: {len(X_test):,}")

model = RandomForestRegressor(
    n_estimators=300,
    max_depth=20,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1,
)

print("\nTraining...")

start = time.perf_counter()

model.fit(X_train, y_train)

training_time = time.perf_counter() - start

print(f"Training time: {training_time:.2f} seconds")

print("\nEvaluating...")

start = time.perf_counter()

val_results = evaluate(model, X_val, y_val)
test_results = evaluate(model, X_test, y_test)

prediction_time = time.perf_counter() - start

print("\nVALIDATION RESULTS")
print("-" * 70)

for key, value in val_results.items():
    print(f"{key:20}: {value:.6f}")

print("\nTEST RESULTS")
print("-" * 70)

for key, value in test_results.items():
    print(f"{key:20}: {value:.6f}")

print(f"\nPrediction time: {prediction_time:.4f} seconds")

print("\nTOP FEATURES")
print("-" * 70)

importance = pd.Series(
    model.feature_importances_,
    index=FEATURES
).sort_values(ascending=False)

print(importance.head(15).to_string())

model_path = MODEL_DIR / "solar_random_forest_baseline.joblib"
results_path = MODEL_DIR / "solar_random_forest_results.json"

joblib.dump(model, model_path)

results = {
    "model": "RandomForestRegressor",
    "n_estimators": 300,
    "max_depth": 20,
    "min_samples_leaf": 2,
    "random_state": 42,
    "feature_count": len(FEATURES),
    "train_rows": len(X_train),
    "validation_rows": len(X_val),
    "test_rows": len(X_test),
    "training_time_seconds": training_time,
    "prediction_time_seconds": prediction_time,
    "validation": val_results,
    "test": test_results,
    "top_features": importance.head(15).to_dict(),
}

with open(results_path, "w") as f:
    json.dump(results, f, indent=2)

print("\nSaved model:")
print(model_path)

print("\nSaved results:")
print(results_path)

print("\n" + "=" * 70)
print("RANDOM FOREST EXPERIMENT COMPLETE")
print("=" * 70)