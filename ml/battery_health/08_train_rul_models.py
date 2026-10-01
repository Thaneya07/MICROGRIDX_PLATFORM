from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
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


# ============================================================
# MODEL PARAMETERS
# ============================================================

RF_PARAMETERS = {
    "n_estimators": 300,
    "max_depth": 20,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}

XGB_PARAMETERS = {
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

    df = pd.read_csv(INPUT_FILE)

    required = (
        FEATURE_COLUMNS
        + [
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
            "Missing values in feature columns."
        )

    if df[TARGET].isna().any():

        raise ValueError(
            "Missing RUL target values."
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
# MODEL FACTORY
# ============================================================

def create_rf():

    return RandomForestRegressor(
        **RF_PARAMETERS
    )


def create_xgb():

    return XGBRegressor(
        **XGB_PARAMETERS
    )


# ============================================================
# RUN MODEL WITH LOBO
# ============================================================

def run_model(
    df,
    model_name,
    model_factory,
):

    batteries = sorted(
        df["battery_id"].unique()
    )

    fold_results = []
    all_predictions = []

    print("\n" + "=" * 70)
    print(f"RUL {model_name.upper()} — LOBO")
    print("=" * 70)

    for test_battery in batteries:

        train_df = df[
            df["battery_id"] != test_battery
        ].copy()

        test_df = df[
            df["battery_id"] == test_battery
        ].copy()

        X_train = train_df[
            FEATURE_COLUMNS
        ]

        y_train = train_df[
            TARGET
        ]

        X_test = test_df[
            FEATURE_COLUMNS
        ]

        y_test = test_df[
            TARGET
        ]

        print(
            f"\nTest battery: {test_battery}"
        )

        print(
            f"Training records: {len(train_df)}"
        )

        print(
            f"Testing records: {len(test_df)}"
        )

        model = model_factory()

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        result = calculate_metrics(
            y_test.to_numpy(),
            y_pred
        )

        result["model"] = model_name
        result["test_battery"] = test_battery
        result["train_records"] = len(train_df)
        result["test_records"] = len(test_df)

        fold_results.append(result)

        pred_df = test_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                TARGET,
            ]
        ].copy()

        pred_df[
            "predicted_rul_cycles"
        ] = y_pred

        pred_df[
            "absolute_error"
        ] = np.abs(
            pred_df[TARGET]
            - pred_df["predicted_rul_cycles"]
        )

        all_predictions.append(pred_df)

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

    fold_df = pd.DataFrame(
        fold_results
    )

    predictions_df = pd.concat(
        all_predictions,
        ignore_index=True
    )

    overall = calculate_metrics(
        predictions_df[TARGET].to_numpy(),
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
# TRAIN FINAL MODEL
# ============================================================

def train_final_model(
    df,
    model_name,
    model_factory,
    filename,
):

    model = model_factory()

    model.fit(
        df[FEATURE_COLUMNS],
        df[TARGET]
    )

    model_path = (
        MODEL_DIR
        / filename
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        f"\nFinal {model_name} model saved to:"
    )

    print(model_path)

    return model, model_path


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    model,
    model_name,
):

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

    filename = (
        "rul_"
        + model_name.lower().replace(" ", "_")
        + "_feature_importance.csv"
    )

    output_file = (
        RESULT_DIR
        / filename
    )

    importance_df.to_csv(
        output_file,
        index=False
    )

    return importance_df, output_file


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX RUL MODEL TRAINING")
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
        f"RUL range: "
        f"{df[TARGET].min():.0f} "
        f"to "
        f"{df[TARGET].max():.0f} cycles"
    )

    # ========================================================
    # RANDOM FOREST
    # ========================================================

    rf_folds, rf_predictions, rf_overall = (
        run_model(
            df,
            "Random Forest",
            create_rf,
        )
    )

    # ========================================================
    # XGBOOST
    # ========================================================

    xgb_folds, xgb_predictions, xgb_overall = (
        run_model(
            df,
            "XGBoost",
            create_xgb,
        )
    )

    # ========================================================
    # OVERALL COMPARISON
    # ========================================================

    comparison = pd.DataFrame(
        [
            {
                "model": "Random Forest",
                **rf_overall,
            },
            {
                "model": "XGBoost",
                **xgb_overall,
            },
        ]
    )

    print("\n" + "=" * 70)
    print("RUL MODEL COMPARISON")
    print("=" * 70)

    print(
        comparison[
            [
                "model",
                "mae",
                "rmse",
                "smape",
                "r2",
            ]
        ].to_string(index=False)
    )

    comparison_file = (
        RESULT_DIR
        / "rul_model_comparison.csv"
    )

    comparison.to_csv(
        comparison_file,
        index=False
    )

    # ========================================================
    # SAVE FOLD RESULTS
    # ========================================================

    rf_folds.to_csv(
        RESULT_DIR
        / "rul_random_forest_lobo_results.csv",
        index=False
    )

    xgb_folds.to_csv(
        RESULT_DIR
        / "rul_xgboost_lobo_results.csv",
        index=False
    )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    rf_predictions.to_csv(
        RESULT_DIR
        / "rul_random_forest_oof_predictions.csv",
        index=False
    )

    xgb_predictions.to_csv(
        RESULT_DIR
        / "rul_xgboost_oof_predictions.csv",
        index=False
    )

    # ========================================================
    # FINAL MODELS
    # ========================================================

    print("\n" + "=" * 70)
    print("TRAINING FINAL MODELS")
    print("=" * 70)

    rf_model, rf_path = train_final_model(
        df,
        "Random Forest",
        create_rf,
        "rul_random_forest.joblib",
    )

    xgb_model, xgb_path = train_final_model(
        df,
        "XGBoost",
        create_xgb,
        "rul_xgboost.joblib",
    )

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    print("\n" + "=" * 70)
    print("RANDOM FOREST TOP FEATURES")
    print("=" * 70)

    rf_importance, rf_importance_file = (
        save_feature_importance(
            rf_model,
            "Random Forest",
        )
    )

    print(
        rf_importance.head(10)
        .to_string(index=False)
    )

    print("\n" + "=" * 70)
    print("XGBOOST TOP FEATURES")
    print("=" * 70)

    xgb_importance, xgb_importance_file = (
        save_feature_importance(
            xgb_model,
            "XGBoost",
        )
    )

    print(
        xgb_importance.head(10)
        .to_string(index=False)
    )

    # ========================================================
    # JSON
    # ========================================================

    summary = {
        "task": "RUL prediction",
        "dataset": str(INPUT_FILE),
        "total_records": int(len(df)),
        "batteries": sorted(
            df["battery_id"].unique()
        ),
        "features": FEATURE_COLUMNS,
        "target": TARGET,
        "evaluation": "leave-one-battery-out",
        "models": {
            "Random Forest": {
                "parameters": RF_PARAMETERS,
                "overall_metrics": rf_overall,
            },
            "XGBoost": {
                "parameters": XGB_PARAMETERS,
                "overall_metrics": xgb_overall,
            },
        },
    }

    summary_file = (
        RESULT_DIR
        / "rul_model_results.json"
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

    print("\n" + "=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print(
        f"\nComparison:\n{comparison_file}"
    )

    print(
        f"\nSummary:\n{summary_file}"
    )

    print("\n" + "#" * 70)
    print("RUL MODEL TRAINING COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()