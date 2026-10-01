from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")

DATA_DIR = (
    BASE_DIR
    / "datasets"
    / "solar"
    / "processed"
)

MODEL_DIR = (
    BASE_DIR
    / "ml"
    / "solar_forecasting"
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

TARGET = "Active_Power"

LOOKBACK = 12

EPOCHS = 30

BATCH_SIZE = 256

RANDOM_STATE = 42


np.random.seed(RANDOM_STATE)

tf.random.set_seed(RANDOM_STATE)


# ============================================================
# LOAD DATA
# ============================================================

train = pd.read_csv(
    DATA_DIR / "solar_train.csv"
)

validation = pd.read_csv(
    DATA_DIR / "solar_validation.csv"
)

test = pd.read_csv(
    DATA_DIR / "solar_test.csv"
)


for df in [train, validation, test]:

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )


# ============================================================
# FEATURES
# ============================================================

DROP_COLUMNS = [
    "timestamp",
    TARGET
]

FEATURES = [
    column
    for column in train.columns
    if column not in DROP_COLUMNS
]


print("=" * 70)
print("SOLAR LSTM")
print("=" * 70)

print(f"Features: {len(FEATURES)}")
print(f"Train: {len(train):,}")
print(f"Validation: {len(validation):,}")
print(f"Test: {len(test):,}")
print(
    f"Lookback: {LOOKBACK} steps "
    f"({LOOKBACK * 5} minutes)"
)


# ============================================================
# SCALE DATA
# ============================================================

feature_scaler = StandardScaler()

target_scaler = StandardScaler()


X_train_raw = train[
    FEATURES
].values.astype(np.float32)

X_val_raw = validation[
    FEATURES
].values.astype(np.float32)

X_test_raw = test[
    FEATURES
].values.astype(np.float32)


y_train_raw = train[
    TARGET
].values.astype(np.float32)

y_val_raw = validation[
    TARGET
].values.astype(np.float32)

y_test_raw = test[
    TARGET
].values.astype(np.float32)


# IMPORTANT:
# Fit scalers ONLY on training data.

X_train_scaled = feature_scaler.fit_transform(
    X_train_raw
)

X_val_scaled = feature_scaler.transform(
    X_val_raw
)

X_test_scaled = feature_scaler.transform(
    X_test_raw
)


y_train_scaled = target_scaler.fit_transform(
    y_train_raw.reshape(-1, 1)
).ravel()

y_val_scaled = target_scaler.transform(
    y_val_raw.reshape(-1, 1)
).ravel()

y_test_scaled = target_scaler.transform(
    y_test_raw.reshape(-1, 1)
).ravel()


# ============================================================
# SEQUENCE CREATION
# ============================================================

def create_sequences(
    X,
    y,
    timestamps,
    lookback
):

    X_sequences = []

    y_sequences = []

    valid_timestamps = []

    timestamps = pd.Series(
        pd.to_datetime(timestamps)
    ).reset_index(drop=True)

    X = np.asarray(X)

    y = np.asarray(y)

    # Find timestamp gaps first.
    timestamp_diff = timestamps.diff()

    valid_positions = np.where(
        timestamp_diff.iloc[
            1:
        ].values
        == pd.Timedelta(minutes=5)
    )[0] + 1

    valid_positions = set(
        valid_positions.tolist()
    )

    for i in range(
        lookback,
        len(X)
    ):

        # The target timestamp must immediately
        # follow the previous observation.
        if i not in valid_positions:
            continue

        # The complete lookback window must contain
        # consecutive 5-minute observations.
        window_start = i - lookback + 1

        window_positions = range(
            window_start,
            i + 1
        )

        if not all(
            position in valid_positions
            for position in window_positions
        ):
            continue

        X_sequences.append(
            X[
                i - lookback:i
            ]
        )

        y_sequences.append(
            y[i]
        )

        valid_timestamps.append(
            timestamps.iloc[i]
        )

    return (
        np.asarray(
            X_sequences,
            dtype=np.float32
        ),
        np.asarray(
            y_sequences,
            dtype=np.float32
        ),
        valid_timestamps
    )


print("\nCreating sequences...")


X_train_seq, y_train_seq, train_seq_times = (
    create_sequences(
        X_train_scaled,
        y_train_scaled,
        train["timestamp"],
        LOOKBACK
    )
)


X_val_seq, y_val_seq, val_seq_times = (
    create_sequences(
        X_val_scaled,
        y_val_scaled,
        validation["timestamp"],
        LOOKBACK
    )
)


X_test_seq, y_test_seq, test_seq_times = (
    create_sequences(
        X_test_scaled,
        y_test_scaled,
        test["timestamp"],
        LOOKBACK
    )
)


print(
    f"Training sequences: "
    f"{len(X_train_seq):,}"
)

print(
    f"Validation sequences: "
    f"{len(X_val_seq):,}"
)

print(
    f"Test sequences: "
    f"{len(X_test_seq):,}"
)


# ============================================================
# SAFETY CHECK
# ============================================================

if (
    len(X_train_seq) == 0
    or len(X_val_seq) == 0
    or len(X_test_seq) == 0
):

    raise RuntimeError(
        "Sequence creation produced zero sequences. "
        "Check timestamp continuity."
    )


print(
    "\nSequence shapes:"
)

print(
    f"Train X: {X_train_seq.shape}"
)

print(
    f"Validation X: {X_val_seq.shape}"
)

print(
    f"Test X: {X_test_seq.shape}"
)


# ============================================================
# MODEL
# ============================================================

model = tf.keras.Sequential([

    tf.keras.layers.Input(
        shape=(
            LOOKBACK,
            len(FEATURES)
        )
    ),

    tf.keras.layers.LSTM(
        64
    ),

    tf.keras.layers.Dropout(
        0.2
    ),

    tf.keras.layers.Dense(
        32,
        activation="relu"
    ),

    tf.keras.layers.Dense(
        1
    )
])


model.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.001
    ),
    loss="mse",
    metrics=["mae"]
)


print("\nModel:")
model.summary()


# ============================================================
# EARLY STOPPING
# ============================================================

callbacks = [

    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    )

]


# ============================================================
# TRAIN
# ============================================================

print("\nTraining LSTM...")

start = time.perf_counter()

history = model.fit(

    X_train_seq,

    y_train_seq,

    validation_data=(
        X_val_seq,
        y_val_seq
    ),

    epochs=EPOCHS,

    batch_size=BATCH_SIZE,

    callbacks=callbacks,

    verbose=1
)

training_time = (
    time.perf_counter()
    - start
)


print(
    f"\nTraining time: "
    f"{training_time:.2f} seconds"
)


# ============================================================
# PREDICTIONS
# ============================================================

print("\nGenerating predictions...")

start = time.perf_counter()


val_pred_scaled = model.predict(
    X_val_seq,
    verbose=0
).ravel()


test_pred_scaled = model.predict(
    X_test_seq,
    verbose=0
).ravel()


prediction_time = (
    time.perf_counter()
    - start
)


# ============================================================
# INVERSE SCALE
# ============================================================

val_pred = target_scaler.inverse_transform(
    val_pred_scaled.reshape(-1, 1)
).ravel()


test_pred = target_scaler.inverse_transform(
    test_pred_scaled.reshape(-1, 1)
).ravel()


# ============================================================
# METRICS
# ============================================================

def smape(
    y_true,
    y_pred
):

    denominator = (
        np.abs(y_true)
        + np.abs(y_pred)
    )

    mask = denominator != 0

    return (
        100
        * np.mean(
            2
            * np.abs(
                y_pred[mask]
                - y_true[mask]
            )
            / denominator[mask]
        )
    )


def evaluate(
    y_true,
    y_pred
):

    return {

        "MAE_W": float(
            mean_absolute_error(
                y_true,
                y_pred
            ) * 1000
        ),

        "RMSE_W": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    y_pred
                )
            ) * 1000
        ),

        "SMAPE_percent": float(
            smape(
                y_true,
                y_pred
            )
        ),

        "R2": float(
            r2_score(
                y_true,
                y_pred
            )
        )
    }


# Use the actual sequence targets.
val_true = target_scaler.inverse_transform(
    y_val_seq.reshape(-1, 1)
).ravel()


test_true = target_scaler.inverse_transform(
    y_test_seq.reshape(-1, 1)
).ravel()


val_results = evaluate(
    val_true,
    val_pred
)


test_results = evaluate(
    test_true,
    test_pred
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\nVALIDATION RESULTS")
print("-" * 70)

for key, value in val_results.items():

    print(
        f"{key:20}: "
        f"{value:.6f}"
    )


print("\nTEST RESULTS")
print("-" * 70)

for key, value in test_results.items():

    print(
        f"{key:20}: "
        f"{value:.6f}"
    )


print(
    f"\nPrediction time: "
    f"{prediction_time:.4f} seconds"
)


print(
    f"Epochs completed: "
    f"{len(history.history['loss'])}"
)


# ============================================================
# SAVE MODEL
# ============================================================

model_path = (
    MODEL_DIR
    / "solar_lstm.keras"
)

model.save(
    model_path
)


# ============================================================
# SAVE SCALERS
# ============================================================

scaler_path = (
    MODEL_DIR
    / "solar_lstm_scalers.joblib"
)

joblib.dump(
    {
        "feature_scaler":
            feature_scaler,

        "target_scaler":
            target_scaler,

        "features":
            FEATURES,

        "lookback":
            LOOKBACK
    },
    scaler_path
)


# ============================================================
# SAVE RESULTS
# ============================================================

results_path = (
    MODEL_DIR
    / "solar_lstm_results.json"
)


results = {

    "model": "LSTM",

    "lookback_steps":
        LOOKBACK,

    "lookback_minutes":
        LOOKBACK * 5,

    "lstm_units":
        64,

    "dense_units":
        32,

    "dropout":
        0.2,

    "batch_size":
        BATCH_SIZE,

    "maximum_epochs":
        EPOCHS,

    "epochs_completed":
        len(history.history["loss"]),

    "random_state":
        RANDOM_STATE,

    "feature_count":
        len(FEATURES),

    "train_sequences":
        len(X_train_seq),

    "validation_sequences":
        len(X_val_seq),

    "test_sequences":
        len(X_test_seq),

    "training_time_seconds":
        training_time,

    "prediction_time_seconds":
        prediction_time,

    "validation":
        val_results,

    "test":
        test_results
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

print("\nSaved scalers:")
print(scaler_path)

print("\nSaved results:")
print(results_path)

print("\n" + "=" * 70)
print("LSTM EXPERIMENT COMPLETE")
print("=" * 70)