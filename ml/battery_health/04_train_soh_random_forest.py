from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


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

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

RESULT_DIR.mkdir(
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

TARGET_COLUMN = "soh_percent"


# ============================================================
# MODEL SETTINGS
# ============================================================

RANDOM_STATE = 42

N_ESTIMATORS = 300

MAX_DEPTH = 20

MIN_SAMPLES_LEAF = 2


# ============================================================
# METRICS
# ============================================================

def smape(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:

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
                y_pred[mask]
                - y_true[mask]
            )
            / denominator[mask]
        )
        * 100.0
    )


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> dict:

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

def load_data() -> pd.DataFrame:

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    required_columns = (
        [
            "battery_id",
            TARGET_COLUMN,
        ]
        + FEATURE_COLUMNS
    )

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing columns:\n"
            + "\n".join(missing)
        )

    if df[FEATURE_COLUMNS].isna().any().any():

        raise ValueError(
            "Missing values found in feature columns."
        )

    if df[TARGET_COLUMN].isna().any():

        raise ValueError(
            "Missing SOH target values found."
        )

    return df


# ============================================================
# CREATE MODEL
# ============================================================

def create_model():

    return RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


# ============================================================
# LEAVE-ONE-BATTERY-OUT
# ============================================================

def run_lobo_cv(
    df: pd.DataFrame,
):

    batteries = sorted(
        df["battery_id"].unique()
    )

    all_predictions = []

    fold_results = []

    print("\n" + "=" * 70)
    print("LEAVE-ONE-BATTERY-OUT EVALUATION")
    print("=" * 70)

    for test_battery in batteries:

        train_df = df[
            df["battery_id"]
            != test_battery
        ].copy()

        test_df = df[
            df["battery_id"]
            == test_battery
        ].copy()

        X_train = train_df[
            FEATURE_COLUMNS
        ]

        y_train = train_df[
            TARGET_COLUMN
        ]

        X_test = test_df[
            FEATURE_COLUMNS
        ]

        y_test = test_df[
            TARGET_COLUMN
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

        model = create_model()

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        metrics = calculate_metrics(
            y_test.to_numpy(),
            y_pred,
        )

        metrics["test_battery"] = test_battery

        metrics["train_records"] = len(
            train_df
        )

        metrics["test_records"] = len(
            test_df
        )

        fold_results.append(metrics)

        print(
            f"MAE  : {metrics['mae']:.6f} %"
        )

        print(
            f"RMSE : {metrics['rmse']:.6f} %"
        )

        print(
            f"SMAPE: {metrics['smape']:.6f} %"
        )

        print(
            f"R²   : {metrics['r2']:.6f}"
        )

        # Store predictions
        fold_predictions = test_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                TARGET_COLUMN,
            ]
        ].copy()

        fold_predictions[
            "predicted_soh_percent"
        ] = y_pred

        fold_predictions[
            "absolute_error"
        ] = np.abs(
            fold_predictions[
                TARGET_COLUMN
            ]
            - fold_predictions[
                "predicted_soh_percent"
            ]
        )

        all_predictions.append(
            fold_predictions
        )

    return (
        pd.DataFrame(fold_results),
        pd.concat(
            all_predictions,
            ignore_index=True
        ),
    )


# ============================================================
# TRAIN FINAL MODEL
# ============================================================

def train_final_model(
    df: pd.DataFrame,
):

    X = df[
        FEATURE_COLUMNS
    ]

    y = df[
        TARGET_COLUMN
    ]

    model = create_model()

    model.fit(
        X,
        y
    )

    model_path = (
        MODEL_DIR
        / "soh_random_forest.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    return model, model_path


# ============================================================
# FEATURE IMPORTANCE
# ============================================================

def save_feature_importance(
    model,
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

    output_file = (
        RESULT_DIR
        / "soh_random_forest_feature_importance.csv"
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
    print("MICROGRIDX SOH RANDOM FOREST")
    print("#" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

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

    fold_results, predictions = (
        run_lobo_cv(df)
    )

    # --------------------------------------------------------
    # Overall out-of-fold metrics
    # --------------------------------------------------------

    y_true = predictions[
        TARGET_COLUMN
    ].to_numpy()

    y_pred = predictions[
        "predicted_soh_percent"
    ].to_numpy()

    overall_metrics = calculate_metrics(
        y_true,
        y_pred
    )

    print("\n" + "=" * 70)
    print("OVERALL OUT-OF-FOLD RESULTS")
    print("=" * 70)

    print(
        f"MAE  : "
        f"{overall_metrics['mae']:.6f} percentage points"
    )

    print(
        f"RMSE : "
        f"{overall_metrics['rmse']:.6f} percentage points"
    )

    print(
        f"SMAPE: "
        f"{overall_metrics['smape']:.6f} %"
    )

    print(
        f"R²   : "
        f"{overall_metrics['r2']:.6f}"
    )

    # --------------------------------------------------------
    # Fold results
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("FOLD RESULTS")
    print("=" * 70)

    print(
        fold_results[
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
        / "soh_random_forest_lobo_results.csv"
    )

    fold_results.to_csv(
        fold_output,
        index=False
    )

    # --------------------------------------------------------
    # Save OOF predictions
    # --------------------------------------------------------

    prediction_output = (
        RESULT_DIR
        / "soh_random_forest_oof_predictions.csv"
    )

    predictions.to_csv(
        prediction_output,
        index=False
    )

    # --------------------------------------------------------
    # Train final production model
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TRAINING FINAL MODEL")
    print("=" * 70)

    final_model, model_path = (
        train_final_model(df)
    )

    print(
        f"Final model saved to:\n{model_path}"
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
    # Save JSON-style summary
    # --------------------------------------------------------

    summary = {
        "model": "RandomForestRegressor",
        "task": "SOH prediction",
        "dataset": str(INPUT_FILE),
        "total_records": int(len(df)),
        "batteries": sorted(
            df["battery_id"].unique()
        ),
        "feature_count": len(
            FEATURE_COLUMNS
        ),
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "evaluation": (
            "leave-one-battery-out "
            "cross-validation"
        ),
        "hyperparameters": {
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH,
            "min_samples_leaf": MIN_SAMPLES_LEAF,
            "random_state": RANDOM_STATE,
        },
        "overall_metrics": overall_metrics,
    }

    import json

    summary_output = (
        RESULT_DIR
        / "soh_random_forest_results.json"
    )

    with open(
        summary_output,
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
        f"{summary_output}"
    )

    print("\n" + "#" * 70)
    print("SOH RANDOM FOREST COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()