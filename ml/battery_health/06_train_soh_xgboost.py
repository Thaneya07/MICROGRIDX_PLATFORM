from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from xgboost import XGBRegressor


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

TARGET = "soh_percent"


# ============================================================
# XGBOOST SETTINGS
# ============================================================

PARAMETERS = {
    "n_estimators": 500,
    "max_depth": 8,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "objective": "reg:squarederror",
    "eval_metric": "rmse",
    "random_state": 42,
    "n_jobs": -1,
}


# ============================================================
# METRICS
# ============================================================

def smape(y_true, y_pred):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    denominator = (
        np.abs(y_true) +
        np.abs(y_pred)
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
# MODEL
# ============================================================

def create_model():

    return XGBRegressor(
        **PARAMETERS
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required = (
        FEATURE_COLUMNS +
        [
            "battery_id",
            TARGET,
        ]
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
            "Missing values detected in features."
        )

    if df[TARGET].isna().any():
        raise ValueError(
            "Missing SOH target values detected."
        )

    return df


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
    print("SOH XGBOOST — LEAVE-ONE-BATTERY-OUT")
    print("=" * 70)

    for test_battery in batteries:

        train_df = df[
            df["battery_id"] != test_battery
        ].copy()

        test_df = df[
            df["battery_id"] == test_battery
        ].copy()

        X_train = train_df[FEATURE_COLUMNS]
        y_train = train_df[TARGET]

        X_test = test_df[FEATURE_COLUMNS]
        y_test = test_df[TARGET]

        print(
            f"\nTest battery: {test_battery}"
        )

        print(
            f"Training records: {len(train_df)}"
        )

        print(
            f"Testing records: {len(test_df)}"
        )

        model = create_model()

        model.fit(
            X_train,
            y_train,
            verbose=False
        )

        y_pred = model.predict(
            X_test
        )

        result = calculate_metrics(
            y_test.to_numpy(),
            y_pred
        )

        result["test_battery"] = test_battery
        result["train_records"] = len(train_df)
        result["test_records"] = len(test_df)

        fold_results.append(result)

        predictions = test_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                TARGET,
            ]
        ].copy()

        predictions["predicted_soh_percent"] = y_pred

        predictions["absolute_error"] = np.abs(
            predictions[TARGET]
            - predictions["predicted_soh_percent"]
        )

        all_predictions.append(
            predictions
        )

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

    fold_df = pd.DataFrame(
        fold_results
    )

    predictions_df = pd.concat(
        all_predictions,
        ignore_index=True
    )

    # Overall OOF
    overall = calculate_metrics(
        predictions_df[TARGET].to_numpy(),
        predictions_df[
            "predicted_soh_percent"
        ].to_numpy()
    )

    return (
        fold_df,
        predictions_df,
        overall
    )


# ============================================================
# FINAL MODEL
# ============================================================

def train_final_model(df):

    model = create_model()

    model.fit(
        df[FEATURE_COLUMNS],
        df[TARGET],
        verbose=False
    )

    model_path = (
        MODEL_DIR
        / "soh_xgboost.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    return model, model_path


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(model):

    importance_df = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance": model.feature_importances_,
        }
    )

    importance_df = (
        importance_df
        .sort_values(
            "importance",
            ascending=False
        )
        .reset_index(drop=True)
    )

    output_file = (
        RESULT_DIR
        / "soh_xgboost_feature_importance.csv"
    )

    importance_df.to_csv(
        output_file,
        index=False
    )

    return (
        importance_df,
        output_file
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX SOH XGBOOST")
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

    # --------------------------------------------------------
    # LOBO evaluation
    # --------------------------------------------------------

    fold_df, predictions_df, overall = (
        run_lobo(df)
    )

    # --------------------------------------------------------
    # Overall results
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("OVERALL OUT-OF-FOLD RESULTS")
    print("=" * 70)

    print(
        f"MAE  : {overall['mae']:.6f} percentage points"
    )

    print(
        f"RMSE : {overall['rmse']:.6f} percentage points"
    )

    print(
        f"SMAPE: {overall['smape']:.6f} %"
    )

    print(
        f"R²   : {overall['r2']:.6f}"
    )

    # --------------------------------------------------------
    # Fold results
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FOLD RESULTS")
    print("=" * 70)

    print(
        fold_df[
            [
                "test_battery",
                "train_records",
                "test_records",
                "mae",
                "rmse",
                "smape",
                "r2",
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # Save fold results
    # --------------------------------------------------------

    fold_output = (
        RESULT_DIR
        / "soh_xgboost_lobo_results.csv"
    )

    fold_df.to_csv(
        fold_output,
        index=False
    )

    # --------------------------------------------------------
    # Save OOF predictions
    # --------------------------------------------------------

    prediction_output = (
        RESULT_DIR
        / "soh_xgboost_oof_predictions.csv"
    )

    predictions_df.to_csv(
        prediction_output,
        index=False
    )

    # --------------------------------------------------------
    # Final model
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TRAINING FINAL MODEL")
    print("=" * 70)

    final_model, model_path = (
        train_final_model(df)
    )

    print(
        f"Model saved to:\n{model_path}"
    )

    # --------------------------------------------------------
    # Feature importance
    # --------------------------------------------------------

    importance_df, importance_output = (
        save_feature_importance(
            final_model
        )
    )

    print("\n" + "=" * 70)
    print("TOP FEATURES")
    print("=" * 70)

    print(
        importance_df
        .head(10)
        .to_string(index=False)
    )

    print(
        f"\nFeature importance saved to:\n"
        f"{importance_output}"
    )

    # --------------------------------------------------------
    # Save JSON summary
    # --------------------------------------------------------

    summary = {
        "model": "XGBRegressor",
        "task": "SOH prediction",
        "evaluation": (
            "leave-one-battery-out"
        ),
        "records": int(len(df)),
        "batteries": sorted(
            df["battery_id"].unique()
        ),
        "features": FEATURE_COLUMNS,
        "target": TARGET,
        "hyperparameters": PARAMETERS,
        "overall_metrics": overall,
    }

    summary_file = (
        RESULT_DIR
        / "soh_xgboost_results.json"
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
        f"\nResults saved to:\n"
        f"{summary_file}"
    )

    print("\n" + "#" * 70)
    print("SOH XGBOOST COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()