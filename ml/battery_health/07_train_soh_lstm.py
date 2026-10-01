from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import StandardScaler

from tensorflow.keras import Sequential
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import (
    LSTM,
    Dense,
    Dropout,
)


# ============================================================
# REPRODUCIBILITY
# ============================================================

RANDOM_STATE = 42

np.random.seed(RANDOM_STATE)
tf.random.set_seed(RANDOM_STATE)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\MicroGridX_PLATFORM\microgridx"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "datasets"
    / "battery_health"
    / "processed"
    / "battery_soh_ml.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "battery_health"
    / "models"
)

RESULT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "battery_health"
    / "results"
)

SCALER_DIR = (
    PROJECT_ROOT
    / "ml"
    / "battery_health"
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SCALER_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FEATURES
# ============================================================

FEATURE_COLUMNS = [
    "ambient_temperature",

    "voltage_mean",
    "voltage_min",
    "voltage_max",
    "voltage_std",

    "current_mean",
    "current_min",
    "current_max",
    "current_std",

    "temperature_mean",
    "temperature_min",
    "temperature_max",
    "temperature_std",

    "duration_sec",

    "current_load_mean",
    "voltage_load_mean",

    "discharge_cycle_index",
]

TARGET = "soh_percent"

# Number of previous/current discharge cycles used
# for each LSTM prediction.
LOOKBACK = 5


# ============================================================
# MODEL SETTINGS
# ============================================================

LSTM_UNITS = 64
DROPOUT = 0.20
DENSE_UNITS = 32

LEARNING_RATE = 0.001

BATCH_SIZE = 16
EPOCHS = 60
PATIENCE = 8


# ============================================================
# METRICS
# ============================================================

def smape(y_true, y_pred):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    denominator = (
        np.abs(y_true)
        + np.abs(y_pred)
    )

    mask = denominator != 0

    if not np.any(mask):
        return 0.0

    return float(
        np.mean(
            2.0
            * np.abs(
                y_pred[mask] - y_true[mask]
            )
            / denominator[mask]
        )
        * 100.0
    )


def calculate_metrics(y_true, y_pred):

    return {
        "mae": float(
            mean_absolute_error(
                y_true,
                y_pred
            )
        ),

        "rmse": float(
            np.sqrt(
                mean_squared_error(
                    y_true,
                    y_pred
                )
            )
        ),

        "smape": smape(
            y_true,
            y_pred
        ),

        "r2": float(
            r2_score(
                y_true,
                y_pred
            )
        ),
    }


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    required = (
        [
            "battery_id",
            "cycle",
        ]
        + FEATURE_COLUMNS
        + [TARGET]
    )

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing columns:\n"
            + "\n".join(missing)
        )

    if df[FEATURE_COLUMNS].isna().any().any():

        raise ValueError(
            "Missing feature values detected."
        )

    if df[TARGET].isna().any():

        raise ValueError(
            "Missing SOH target values detected."
        )

    # Always maintain battery-wise chronological order.
    df = (
        df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )

    return df


# ============================================================
# CREATE SEQUENCES
# ============================================================

def create_sequences(
    df,
    scaler,
    fit_scaler,
):

    X_sequences = []
    y_values = []

    metadata = []

    battery_groups = (
        df
        .groupby(
            "battery_id",
            sort=False
        )
    )

    for battery_id, group in battery_groups:

        group = (
            group
            .sort_values(
                "discharge_cycle_index"
            )
            .reset_index(drop=True)
        )

        X_raw = group[
            FEATURE_COLUMNS
        ].to_numpy(
            dtype=np.float32
        )

        y = group[
            TARGET
        ].to_numpy(
            dtype=np.float32
        )

        # ----------------------------------------------------
        # Fit scaler ONLY on training data
        # ----------------------------------------------------

        if fit_scaler:

            scaler.partial_fit(
                X_raw
            )

        # ----------------------------------------------------
        # Scale using training-fitted scaler
        # ----------------------------------------------------

        X_scaled = scaler.transform(
            X_raw
        ).astype(
            np.float32
        )

        # ----------------------------------------------------
        # Create sequences
        #
        # Sequence contains:
        # LOOKBACK consecutive discharge cycles
        #
        # Target = SOH of final cycle in sequence.
        # ----------------------------------------------------

        if len(group) <= LOOKBACK:
            continue

        for end_idx in range(
            LOOKBACK - 1,
            len(group)
        ):

            start_idx = (
                end_idx
                - LOOKBACK
                + 1
            )

            sequence = X_scaled[
                start_idx:end_idx + 1
            ]

            X_sequences.append(
                sequence
            )

            y_values.append(
                y[end_idx]
            )

            metadata.append(
                {
                    "battery_id": battery_id,
                    "cycle": int(
                        group.loc[
                            end_idx,
                            "cycle"
                        ]
                    ),
                    "discharge_cycle_index": int(
                        group.loc[
                            end_idx,
                            "discharge_cycle_index"
                        ]
                    ),
                }
            )

    X = np.asarray(
        X_sequences,
        dtype=np.float32
    )

    y = np.asarray(
        y_values,
        dtype=np.float32
    )

    metadata_df = pd.DataFrame(
        metadata
    )

    return X, y, metadata_df


# ============================================================
# BUILD LSTM
# ============================================================

def build_model(
    n_features
):

    model = Sequential(
        [
            LSTM(
                LSTM_UNITS,
                input_shape=(
                    LOOKBACK,
                    n_features,
                ),
            ),

            Dropout(
                DROPOUT
            ),

            Dense(
                DENSE_UNITS,
                activation="relu"
            ),

            Dense(
                1
            ),
        ]
    )

    optimizer = tf.keras.optimizers.Adam(
        learning_rate=LEARNING_RATE
    )

    model.compile(
        optimizer=optimizer,
        loss="mse",
        metrics=["mae"],
    )

    return model


# ============================================================
# LEAVE-ONE-BATTERY-OUT
# ============================================================

def run_lobo(df):

    batteries = sorted(
        df["battery_id"].unique()
    )

    fold_results = []
    all_predictions = []

    print("\n" + "=" * 70)
    print("SOH LSTM — LEAVE-ONE-BATTERY-OUT")
    print("=" * 70)

    for test_battery in batteries:

        print("\n" + "-" * 70)
        print(
            f"Test battery: {test_battery}"
        )
        print("-" * 70)

        train_df = df[
            df["battery_id"]
            != test_battery
        ].copy()

        test_df = df[
            df["battery_id"]
            == test_battery
        ].copy()

        print(
            f"Training records: "
            f"{len(train_df)}"
        )

        print(
            f"Testing records: "
            f"{len(test_df)}"
        )

        # ----------------------------------------------------
        # Fit scaler ONLY using training batteries
        # ----------------------------------------------------

        scaler = StandardScaler()

        # Fit on all training battery feature rows.
        scaler.fit(
            train_df[
                FEATURE_COLUMNS
            ].to_numpy(
                dtype=np.float32
            )
        )

        # ----------------------------------------------------
        # Create training sequences
        # ----------------------------------------------------

        X_train, y_train, _ = create_sequences(
            train_df,
            scaler,
            fit_scaler=False,
        )

        # ----------------------------------------------------
        # Create test sequences
        # ----------------------------------------------------

        X_test, y_test, test_metadata = (
            create_sequences(
                test_df,
                scaler,
                fit_scaler=False,
            )
        )

        print(
            f"Training sequences: "
            f"{len(X_train)}"
        )

        print(
            f"Testing sequences: "
            f"{len(X_test)}"
        )

        if len(X_train) == 0:

            raise RuntimeError(
                "No training sequences generated."
            )

        if len(X_test) == 0:

            raise RuntimeError(
                "No test sequences generated."
            )

        # ----------------------------------------------------
        # Build model
        # ----------------------------------------------------

        model = build_model(
            len(FEATURE_COLUMNS)
        )

        early_stopping = EarlyStopping(
            monitor="val_loss",
            patience=PATIENCE,
            restore_best_weights=True,
        )

        # ----------------------------------------------------
        # Train
        # ----------------------------------------------------

        start_time = time.perf_counter()

        history = model.fit(
            X_train,
            y_train,
            validation_split=0.15,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=[
                early_stopping
            ],
            verbose=0,
            shuffle=False,
        )

        training_time = (
            time.perf_counter()
            - start_time
        )

        # ----------------------------------------------------
        # Predict
        # ----------------------------------------------------

        start_prediction = (
            time.perf_counter()
        )

        y_pred = (
            model
            .predict(
                X_test,
                verbose=0
            )
            .reshape(-1)
        )

        prediction_time = (
            time.perf_counter()
            - start_prediction
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        result = calculate_metrics(
            y_test,
            y_pred
        )

        result[
            "test_battery"
        ] = test_battery

        result[
            "train_records"
        ] = len(train_df)

        result[
            "test_records"
        ] = len(test_df)

        result[
            "train_sequences"
        ] = len(X_train)

        result[
            "test_sequences"
        ] = len(X_test)

        result[
            "epochs"
        ] = len(
            history.history["loss"]
        )

        result[
            "training_time_sec"
        ] = float(
            training_time
        )

        result[
            "prediction_time_sec"
        ] = float(
            prediction_time
        )

        fold_results.append(
            result
        )

        # ----------------------------------------------------
        # Store predictions
        # ----------------------------------------------------

        prediction_df = test_metadata.copy()

        prediction_df[
            "soh_percent"
        ] = y_test

        prediction_df[
            "predicted_soh_percent"
        ] = y_pred

        prediction_df[
            "absolute_error"
        ] = np.abs(
            y_test - y_pred
        )

        all_predictions.append(
            prediction_df
        )

        # ----------------------------------------------------
        # Print fold
        # ----------------------------------------------------

        print(
            f"MAE  : {result['mae']:.6f} %"
        )

        print(
            f"RMSE : {result['rmse']:.6f} %"
        )

        print(
            f"SMAPE: {result['smape']:.6f} %"
        )

        print(
            f"R²   : {result['r2']:.6f}"
        )

        print(
            f"Epochs: {result['epochs']}"
        )

        print(
            f"Training time: "
            f"{training_time:.2f} sec"
        )

    fold_df = pd.DataFrame(
        fold_results
    )

    predictions_df = pd.concat(
        all_predictions,
        ignore_index=True
    )

    overall = calculate_metrics(
        predictions_df[
            "soh_percent"
        ].to_numpy(),
        predictions_df[
            "predicted_soh_percent"
        ].to_numpy(),
    )

    return (
        fold_df,
        predictions_df,
        overall,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX SOH LSTM")
    print("#" * 70)

    df = load_data()

    print(
        f"\nTotal records: {len(df)}"
    )

    print(
        f"Batteries: "
        f"{df['battery_id'].nunique()}"
    )

    print(
        f"Features: "
        f"{len(FEATURE_COLUMNS)}"
    )

    print(
        f"Lookback: "
        f"{LOOKBACK} discharge cycles"
    )

    # --------------------------------------------------------
    # LOBO
    # --------------------------------------------------------

    (
        fold_df,
        predictions_df,
        overall,
    ) = run_lobo(df)

    # ========================================================
    # OVERALL
    # ========================================================

    print("\n" + "=" * 70)
    print("OVERALL OUT-OF-FOLD RESULTS")
    print("=" * 70)

    print(
        f"MAE  : "
        f"{overall['mae']:.6f} percentage points"
    )

    print(
        f"RMSE : "
        f"{overall['rmse']:.6f} percentage points"
    )

    print(
        f"SMAPE: "
        f"{overall['smape']:.6f} %"
    )

    print(
        f"R²   : "
        f"{overall['r2']:.6f}"
    )

    # ========================================================
    # FOLDS
    # ========================================================

    print("\n" + "=" * 70)
    print("FOLD RESULTS")
    print("=" * 70)

    print(
        fold_df[
            [
                "test_battery",
                "train_sequences",
                "test_sequences",
                "mae",
                "rmse",
                "smape",
                "r2",
                "epochs",
                "training_time_sec",
            ]
        ].to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    fold_output = (
        RESULT_DIR
        / "soh_lstm_lobo_results.csv"
    )

    prediction_output = (
        RESULT_DIR
        / "soh_lstm_oof_predictions.csv"
    )

    fold_df.to_csv(
        fold_output,
        index=False
    )

    predictions_df.to_csv(
        prediction_output,
        index=False
    )

    # ========================================================
    # TRAIN FINAL MODEL ON ALL BATTERIES
    # ========================================================

    print("\n" + "=" * 70)
    print("TRAINING FINAL SOH LSTM")
    print("=" * 70)

    final_scaler = StandardScaler()

    final_scaler.fit(
        df[
            FEATURE_COLUMNS
        ].to_numpy(
            dtype=np.float32
        )
    )

    X_all, y_all, _ = create_sequences(
        df,
        final_scaler,
        fit_scaler=False,
    )

    final_model = build_model(
        len(FEATURE_COLUMNS)
    )

    final_early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=PATIENCE,
        restore_best_weights=True,
    )

    final_history = final_model.fit(
        X_all,
        y_all,
        validation_split=0.15,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[
            final_early_stopping
        ],
        verbose=0,
        shuffle=False,
    )

    final_model_path = (
        MODEL_DIR
        / "soh_lstm.keras"
    )

    final_scaler_path = (
        SCALER_DIR
        / "soh_lstm_scaler.joblib"
    )

    final_model.save(
        final_model_path
    )

    joblib.dump(
        final_scaler,
        final_scaler_path
    )

    print(
        f"Final model saved to:\n"
        f"{final_model_path}"
    )

    print(
        f"Scaler saved to:\n"
        f"{final_scaler_path}"
    )

    print(
        f"Final training sequences: "
        f"{len(X_all)}"
    )

    print(
        f"Final epochs: "
        f"{len(final_history.history['loss'])}"
    )

    # ========================================================
    # JSON SUMMARY
    # ========================================================

    summary = {
        "model": "LSTM",
        "task": "SOH prediction",
        "evaluation": (
            "leave-one-battery-out"
        ),
        "total_records": int(
            len(df)
        ),
        "batteries": sorted(
            df["battery_id"].unique()
        ),
        "feature_count": len(
            FEATURE_COLUMNS
        ),
        "features": FEATURE_COLUMNS,
        "target": TARGET,
        "lookback": LOOKBACK,
        "hyperparameters": {
            "lstm_units": LSTM_UNITS,
            "dropout": DROPOUT,
            "dense_units": DENSE_UNITS,
            "learning_rate": LEARNING_RATE,
            "batch_size": BATCH_SIZE,
            "epochs": EPOCHS,
            "patience": PATIENCE,
            "random_state": RANDOM_STATE,
        },
        "overall_metrics": overall,
    }

    summary_file = (
        RESULT_DIR
        / "soh_lstm_results.json"
    )

    with open(
        summary_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=2
        )

    print(
        f"\nResults summary saved to:\n"
        f"{summary_file}"
    )

    print("\n" + "#" * 70)
    print("SOH LSTM COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()