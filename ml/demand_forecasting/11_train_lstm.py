from pathlib import Path
import json
import time

import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from tensorflow.keras import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping


# ============================================================
# MicroGridX - Demand Forecasting
# Step 13: Gap-Safe LSTM
# ============================================================

SEED = 42
LOOKBACK = 48                 # 48 x 30 min = 24 hours
EXPECTED_INTERVAL = pd.Timedelta(minutes=30)

np.random.seed(SEED)
tf.random.set_seed(SEED)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
    / "demand_30min.csv"
)

MODEL_DIR = (
    BASE_DIR
    / "ml"
    / "demand_forecasting"
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MODEL_PATH = MODEL_DIR / "lstm_gap_safe.keras"
RESULTS_PATH = MODEL_DIR / "lstm_gap_safe_results.json"


print("=" * 70)
print("MicroGridX Demand Forecasting - Gap-Safe LSTM")
print("=" * 70)


# ------------------------------------------------------------
# Load 30-minute dataset
# ------------------------------------------------------------

print("\nLoading 30-minute dataset...")

df = pd.read_csv(DATA_PATH)

df["timestamp"] = pd.to_datetime(
    df["timestamp"]
)

df = (
    df.sort_values("timestamp")
    .reset_index(drop=True)
)

print(f"Total rows: {len(df):,}")


# ------------------------------------------------------------
# Required columns
# ------------------------------------------------------------

FEATURES = [
    "demand_w",
    "hour",
    "minute",
    "day_of_week",
    "is_weekend",
]

TARGET = "demand_w"


# ------------------------------------------------------------
# Create continuous segments
# ------------------------------------------------------------

print("\nIdentifying continuous 30-minute segments...")

time_difference = (
    df["timestamp"].diff()
)

new_segment = (
    time_difference != EXPECTED_INTERVAL
)

df["segment_id"] = (
    new_segment.cumsum()
)

number_of_segments = (
    df["segment_id"].nunique()
)

print(
    f"Continuous segments: "
    f"{number_of_segments:,}"
)


# ------------------------------------------------------------
# Fit scaler ONLY on training-period observations
# ------------------------------------------------------------

# Use the same chronological boundaries as our enhanced
# Random Forest experiment.

train_end = pd.Timestamp(
    "2009-09-15 18:30:00"
)

validation_end = pd.Timestamp(
    "2010-04-19 19:00:00"
)

train_raw = df[
    df["timestamp"] <= train_end
].copy()

validation_raw = df[
    (df["timestamp"] > train_end)
    & (df["timestamp"] <= validation_end)
].copy()

test_raw = df[
    df["timestamp"] > validation_end
].copy()


print("\nChronological periods:")

print(
    f"Training   : {train_raw['timestamp'].min()} "
    f"→ {train_raw['timestamp'].max()}"
)

print(
    f"Validation : {validation_raw['timestamp'].min()} "
    f"→ {validation_raw['timestamp'].max()}"
)

print(
    f"Test       : {test_raw['timestamp'].min()} "
    f"→ {test_raw['timestamp'].max()}"
)


# ------------------------------------------------------------
# Scale numerical sequence features
# ------------------------------------------------------------

print("\nFitting scaler using training data only...")

scaler = StandardScaler()

scaler.fit(
    train_raw[FEATURES]
)


# ------------------------------------------------------------
# Sequence creation
# ------------------------------------------------------------

def create_sequences(
    data,
    scaler,
    lookback,
):

    X_sequences = []
    y_values = []
    timestamps = []

    # Process each continuous segment separately.
    for _, segment in data.groupby(
        "segment_id"
    ):

        segment = (
            segment
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        if len(segment) <= lookback:
            continue

        scaled = scaler.transform(
            segment[FEATURES]
        )

        for i in range(
            lookback,
            len(segment)
        ):

            X_sequences.append(
                scaled[
                    i - lookback:i
                ]
            )

            # Target is the next observation after
            # the 48-step history.
            y_values.append(
                segment.loc[
                    i,
                    TARGET
                ]
            )

            timestamps.append(
                segment.loc[
                    i,
                    "timestamp"
                ]
            )

    return (
        np.asarray(
            X_sequences,
            dtype=np.float32
        ),
        np.asarray(
            y_values,
            dtype=np.float32
        ),
        pd.to_datetime(timestamps),
    )


print("\nCreating training sequences...")

X_train, y_train, train_times = (
    create_sequences(
        train_raw,
        scaler,
        LOOKBACK,
    )
)

print("\nCreating validation sequences...")

X_val, y_val, val_times = (
    create_sequences(
        validation_raw,
        scaler,
        LOOKBACK,
    )
)

print("\nCreating test sequences...")

X_test, y_test, test_times = (
    create_sequences(
        test_raw,
        scaler,
        LOOKBACK,
    )
)


print("\n" + "=" * 70)
print("SEQUENCE SUMMARY")
print("=" * 70)

print(
    f"Training sequences   : {len(X_train):,}"
)

print(
    f"Validation sequences : {len(X_val):,}"
)

print(
    f"Test sequences       : {len(X_test):,}"
)

print(
    f"Input shape          : {X_train.shape[1:]}"
)


# ------------------------------------------------------------
# Safety checks
# ------------------------------------------------------------

if len(X_train) == 0:
    raise ValueError(
        "No training sequences were created."
    )

if len(X_val) == 0:
    raise ValueError(
        "No validation sequences were created."
    )

if len(X_test) == 0:
    raise ValueError(
        "No test sequences were created."
    )


# ------------------------------------------------------------
# Build LSTM
# ------------------------------------------------------------

print("\nBuilding LSTM...")

model = Sequential(
    [
        LSTM(
            64,
            input_shape=(
                X_train.shape[1],
                X_train.shape[2],
            ),
        ),

        Dropout(0.2),

        Dense(
            32,
            activation="relu"
        ),

        Dense(1),
    ]
)

model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"],
)


# ------------------------------------------------------------
# Early stopping
# ------------------------------------------------------------

early_stopping = EarlyStopping(
    monitor="val_loss",
    patience=5,
    restore_best_weights=True,
)


# ------------------------------------------------------------
# Train
# ------------------------------------------------------------

print("\nTraining LSTM...")

start_time = time.perf_counter()

history = model.fit(
    X_train,
    y_train,
    validation_data=(
        X_val,
        y_val
    ),
    epochs=30,
    batch_size=128,
    callbacks=[
        early_stopping
    ],
    verbose=1,
)

training_time = (
    time.perf_counter()
    - start_time
)


# ------------------------------------------------------------
# Predict
# ------------------------------------------------------------

print("\nGenerating predictions...")

prediction_start = time.perf_counter()

predictions = model.predict(
    X_test,
    verbose=0
).reshape(-1)

prediction_time = (
    time.perf_counter()
    - prediction_start
)


# ------------------------------------------------------------
# Metrics
# ------------------------------------------------------------

mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        predictions
    )
)

r2 = r2_score(
    y_test,
    predictions
)

denominator = (
    np.abs(y_test)
    + np.abs(predictions)
)

valid = denominator != 0

smape = np.mean(
    2
    * np.abs(
        predictions[valid]
        - y_test[valid]
    )
    / denominator[valid]
) * 100


# ------------------------------------------------------------
# Results
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("LSTM FINAL TEST RESULTS")
print("=" * 70)

print(
    f"MAE_W                   : {mae:.6f}"
)

print(
    f"RMSE_W                  : {rmse:.6f}"
)

print(
    f"SMAPE_percent           : {smape:.6f}"
)

print(
    f"R2                      : {r2:.6f}"
)

print(
    f"Training_time_seconds   : "
    f"{training_time:.6f}"
)

print(
    f"Prediction_time_seconds : "
    f"{prediction_time:.6f}"
)

print(
    f"Epochs_completed        : "
    f"{len(history.history['loss'])}"
)

print(
    f"Test predictions        : "
    f"{len(predictions):,}"
)


# ------------------------------------------------------------
# Save model
# ------------------------------------------------------------

model.save(
    MODEL_PATH
)

print("\nModel saved to:")
print(MODEL_PATH)


# ------------------------------------------------------------
# Save results
# ------------------------------------------------------------

results = {
    "model": "Gap-Safe LSTM",

    "seed": SEED,

    "lookback_steps": LOOKBACK,

    "lookback_minutes": LOOKBACK * 30,

    "features": FEATURES,

    "training_sequences": int(
        len(X_train)
    ),

    "validation_sequences": int(
        len(X_val)
    ),

    "test_sequences": int(
        len(X_test)
    ),

    "training_time_seconds": (
        float(training_time)
    ),

    "prediction_time_seconds": (
        float(prediction_time)
    ),

    "epochs_completed": int(
        len(history.history["loss"])
    ),

    "test": {
        "MAE_W": float(mae),
        "RMSE_W": float(rmse),
        "SMAPE_percent": float(smape),
        "R2": float(r2),
    },
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

print("\nGap-safe LSTM experiment complete.")