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
    Input,
    LSTM,
    Dropout,
    Dense,
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
    / "battery_rul_ml.csv"
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

MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


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

TARGET = "rul_cycles"

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
        "r2": float(
            r2_score(
                y_true,
                y_pred
            )
        ),
    }


def calculate_smape(y_true, y_pred):

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
            * np.abs(y_pred[mask] - y_true[mask])
            / denominator[mask]
        )
        * 100.0
    )


# ============================================================
# LOAD
# ============================================================

def load_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = (
        [
            "battery_id",
            "cycle",
        ]
        + FEATURE_COLUMNS
        + [TARGET]
    )

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns:\n"
            + "\n".join(missing)
        )

    if df[FEATURE_COLUMNS].isna().any().any():
        raise ValueError(
            "Missing feature values found."
        )

    if df[TARGET].isna().any():
        raise ValueError(
            "Missing RUL values found."
        )

    return (
        df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# CREATE SEQUENCES
# ============================================================

def create_sequences(
    df,
    scaler,
):

    X_sequences = []
    y_values = []
    metadata = []

    for battery_id, group in df.groupby(
        "battery_id",
        sort=False
    ):

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

        X_scaled = scaler.transform(
            X_raw
        ).astype(np.float32)

        if len(group) < LOOKBACK:
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

            X_sequences.append(
                X_scaled[
                    start_idx:end_idx + 1
                ]
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

    return (
        np.asarray(
            X_sequences,
            dtype=np.float32
        ),
        np.asarray(
            y_values,
            dtype=np.float32
        ),
        pd.DataFrame(metadata),
    )


# ============================================================
# MODEL
# ============================================================

def build_model(n_features):

    model = Sequential(
        [
            Input(
                shape=(
                    LOOKBACK,
                    n_features,
                )
            ),

            LSTM(
                LSTM_UNITS
            ),

            Dropout(
                DROPOUT
            ),

            Dense(
                DENSE_UNITS,
                activation="relu"
            ),

            Dense(1),
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
# LOBO
# ============================================================

def run_lobo(df):

    batteries = sorted(
        df["battery_id"].unique()
    )

    fold_results = []
    all_predictions = []

    print("\n" + "=" * 70)
    print("RUL LSTM — LEAVE-ONE-BATTERY-OUT")
    print("=" * 70)

    for test_battery in batteries:

        print("\n" + "-" * 70)
        print(
            f"Test battery: {test_battery}"
        )
        print("-" * 70)

        train_df = df[
            df["battery_id"] != test_battery
        ].copy()

        test_df = df[
            df["battery_id"] == test_battery
        ].copy()

        # ----------------------------------------------------
        # Fit scaler ONLY on training batteries
        # ----------------------------------------------------

        scaler = StandardScaler()

        scaler.fit(
            train_df[
                FEATURE_COLUMNS
            ].to_numpy(
                dtype=np.float32
            )
        )

        # ----------------------------------------------------
        # Sequences
        # ----------------------------------------------------

        X_train, y_train, _ = (
            create_sequences(
                train_df,
                scaler
            )
        )

        X_test, y_test, test_meta = (
            create_sequences(
                test_df,
                scaler
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
        # Model
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

        start = time.perf_counter()

        history = model.fit(
            X_train,
            y_train,
            validation_split=0.15,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=[early_stopping],
            verbose=0,
            shuffle=False,
        )

        training_time = (
            time.perf_counter() - start
        )

        # ----------------------------------------------------
        # Predict
        # ----------------------------------------------------

        start_pred = time.perf_counter()

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
            - start_pred
        )

        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------

        result = calculate_metrics(
            y_test,
            y_pred
        )

        result["smape"] = calculate_smape(
            y_test,
            y_pred
        )

        result["test_battery"] = (
            test_battery
        )

        result["train_records"] = len(
            train_df
        )

        result["test_records"] = len(
            test_df
        )

        result["train_sequences"] = len(
            X_train
        )

        result["test_sequences"] = len(
            X_test
        )

        result["epochs"] = len(
            history.history["loss"]
        )

        result["training_time_sec"] = (
            float(training_time)
        )

        result["prediction_time_sec"] = (
            float(prediction_time)
        )

        fold_results.append(result)

        # ----------------------------------------------------
        # Predictions
        # ----------------------------------------------------

        pred_df = test_meta.copy()

        pred_df["rul_cycles"] = y_test

        pred_df[
            "predicted_rul_cycles"
        ] = y_pred

        pred_df["absolute_error"] = np.abs(
            y_test - y_pred
        )

        all_predictions.append(
            pred_df
        )

        print(
            f"MAE  : {result['mae']:.6f} cycles"
        )

        print(
            f"RMSE : {result['rmse']:.6f} cycles"
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
            "rul_cycles"
        ].to_numpy(),
        predictions_df[
            "predicted_rul_cycles"
        ].to_numpy()
    )

    overall["smape"] = calculate_smape(
        predictions_df[
            "rul_cycles"
        ].to_numpy(),
        predictions_df[
            "predicted_rul_cycles"
        ].to_numpy()
    )

    return (
        fold_df,
        predictions_df,
        overall,
    )


# ============================================================
# FINAL MODEL
# ============================================================

def train_final_model(df):

    scaler = StandardScaler()

    scaler.fit(
        df[
            FEATURE_COLUMNS
        ].to_numpy(
            dtype=np.float32
        )
    )

    X_all, y_all, _ = create_sequences(
        df,
        scaler
    )

    model = build_model(
        len(FEATURE_COLUMNS)
    )

    early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=PATIENCE,
        restore_best_weights=True,
    )

    history = model.fit(
        X_all,
        y_all,
        validation_split=0.15,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=[early_stopping],
        verbose=0,
        shuffle=False,
    )

    model_path = (
        MODEL_DIR
        / "rul_lstm.keras"
    )

    scaler_path = (
        MODEL_DIR
        / "rul_lstm_scaler.joblib"
    )

    model.save(
        model_path
    )

    joblib.dump(
        scaler,
        scaler_path
    )

    return (
        model_path,
        scaler_path,
        len(X_all),
        len(
            history.history["loss"]
        ),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX RUL LSTM")
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

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("OVERALL OUT-OF-FOLD RESULTS")
    print("=" * 70)

    print(
        f"MAE  : "
        f"{overall['mae']:.6f} cycles"
    )

    print(
        f"RMSE : "
        f"{overall['rmse']:.6f} cycles"
    )

    print(
        f"SMAPE: "
        f"{overall['smape']:.6f} %"
    )

    print(
        f"R²   : "
        f"{overall['r2']:.6f}"
    )

    # --------------------------------------------------------
    # Folds
    # --------------------------------------------------------

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
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    fold_file = (
        RESULT_DIR
        / "rul_lstm_lobo_results.csv"
    )

    predictions_file = (
        RESULT_DIR
        / "rul_lstm_oof_predictions.csv"
    )

    fold_df.to_csv(
        fold_file,
        index=False
    )

    predictions_df.to_csv(
        predictions_file,
        index=False
    )

    # --------------------------------------------------------
    # Final model
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TRAINING FINAL RUL LSTM")
    print("=" * 70)

    (
        model_path,
        scaler_path,
        total_sequences,
        epochs,
    ) = train_final_model(df)

    print(
        f"Final model saved to:\n"
        f"{model_path}"
    )

    print(
        f"Scaler saved to:\n"
        f"{scaler_path}"
    )

    print(
        f"Final sequences: "
        f"{total_sequences}"
    )

    print(
        f"Final epochs: "
        f"{epochs}"
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    summary = {
        "model": "LSTM",
        "task": "RUL prediction",
        "evaluation": "leave-one-battery-out",
        "records": int(len(df)),
        "batteries": sorted(
            df["battery_id"].unique()
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
        / "rul_lstm_results.json"
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
    print("RUL LSTM COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()