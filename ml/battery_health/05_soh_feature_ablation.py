from pathlib import Path

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

RESULT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "battery_health"
    / "results"
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FEATURE SET
# ============================================================

ALL_FEATURES = [
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


EXPERIMENTS = {
    "Full": ALL_FEATURES,

    "No_Duration": [
        feature
        for feature in ALL_FEATURES
        if feature != "duration_sec"
    ],

    "No_Duration_No_Cycle": [
        feature
        for feature in ALL_FEATURES
        if feature not in [
            "duration_sec",
            "discharge_cycle_index",
        ]
    ],
}


# ============================================================
# MODEL
# ============================================================

def create_model():

    return RandomForestRegressor(
        n_estimators=300,
        max_depth=20,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )


# ============================================================
# SMAPE
# ============================================================

def calculate_smape(
    y_true,
    y_pred,
):

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
                y_pred[mask]
                - y_true[mask]
            )
            / denominator[mask]
        )
        * 100.0
    )


# ============================================================
# METRICS
# ============================================================

def metrics(
    y_true,
    y_pred,
):

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

        "smape": calculate_smape(
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
# RUN ONE EXPERIMENT
# ============================================================

def run_experiment(
    df,
    experiment_name,
    features,
):

    batteries = sorted(
        df["battery_id"].unique()
    )

    predictions = []

    fold_results = []

    print("\n" + "=" * 70)
    print(f"EXPERIMENT: {experiment_name}")
    print("=" * 70)

    print(
        f"Feature count: {len(features)}"
    )

    for test_battery in batteries:

        train_df = df[
            df["battery_id"]
            != test_battery
        ]

        test_df = df[
            df["battery_id"]
            == test_battery
        ]

        X_train = train_df[features]
        y_train = train_df[TARGET]

        X_test = test_df[features]
        y_test = test_df[TARGET]

        model = create_model()

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        result = metrics(
            y_test.to_numpy(),
            y_pred,
        )

        result["experiment"] = experiment_name
        result["test_battery"] = test_battery
        result["feature_count"] = len(features)

        fold_results.append(result)

        fold_prediction = test_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                TARGET,
            ]
        ].copy()

        fold_prediction[
            "predicted_soh_percent"
        ] = y_pred

        predictions.append(
            fold_prediction
        )

        print(
            f"\nTest battery: {test_battery}"
        )

        print(
            f"MAE  : {result['mae']:.6f}"
        )

        print(
            f"RMSE : {result['rmse']:.6f}"
        )

        print(
            f"SMAPE: {result['smape']:.6f}"
        )

        print(
            f"R²   : {result['r2']:.6f}"
        )

    predictions_df = pd.concat(
        predictions,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Overall out-of-fold metrics
    # --------------------------------------------------------

    overall = metrics(
        predictions_df[TARGET].to_numpy(),
        predictions_df[
            "predicted_soh_percent"
        ].to_numpy(),
    )

    overall["experiment"] = experiment_name
    overall["test_battery"] = "OVERALL"
    overall["feature_count"] = len(features)

    fold_df = pd.DataFrame(
        fold_results
    )

    overall_df = pd.DataFrame(
        [overall]
    )

    return (
        overall_df,
        fold_df,
        predictions_df,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("SOH FEATURE ABLATION EXPERIMENT")
    print("#" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Dataset not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"\nDataset rows: {len(df)}"
    )

    print(
        f"Batteries: "
        f"{df['battery_id'].nunique()}"
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    required_columns = (
        ALL_FEATURES
        + [
            "battery_id",
            TARGET,
        ]
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

    # --------------------------------------------------------
    # Run experiments
    # --------------------------------------------------------

    all_overall = []
    all_folds = []

    for experiment_name, features in (
        EXPERIMENTS.items()
    ):

        overall_df, fold_df, predictions_df = (
            run_experiment(
                df,
                experiment_name,
                features,
            )
        )

        all_overall.append(
            overall_df
        )

        all_folds.append(
            fold_df
        )

        # Save predictions for each experiment
        prediction_file = (
            RESULT_DIR
            / f"soh_ablation_{experiment_name.lower()}"
            "_predictions.csv"
        )

        predictions_df.to_csv(
            prediction_file,
            index=False
        )

    # --------------------------------------------------------
    # Combine results
    # --------------------------------------------------------

    overall_results = pd.concat(
        all_overall,
        ignore_index=True
    )

    fold_results = pd.concat(
        all_folds,
        ignore_index=True
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    overall_file = (
        RESULT_DIR
        / "soh_feature_ablation_overall.csv"
    )

    fold_file = (
        RESULT_DIR
        / "soh_feature_ablation_folds.csv"
    )

    overall_results.to_csv(
        overall_file,
        index=False
    )

    fold_results.to_csv(
        fold_file,
        index=False
    )

    # ========================================================
    # FINAL COMPARISON
    # ========================================================

    print("\n" + "=" * 70)
    print("OVERALL ABLATION COMPARISON")
    print("=" * 70)

    print(
        overall_results[
            [
                "experiment",
                "feature_count",
                "mae",
                "rmse",
                "smape",
                "r2",
            ]
        ]
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Relative difference from Full model
    # --------------------------------------------------------

    full = overall_results[
        overall_results["experiment"]
        == "Full"
    ].iloc[0]

    comparison = []

    for _, row in overall_results.iterrows():

        comparison.append(
            {
                "experiment": row["experiment"],

                "mae": row["mae"],

                "mae_change_vs_full": (
                    row["mae"]
                    - full["mae"]
                ),

                "mae_change_percent": (
                    (
                        row["mae"]
                        - full["mae"]
                    )
                    / full["mae"]
                    * 100.0
                ),

                "rmse": row["rmse"],

                "rmse_change_vs_full": (
                    row["rmse"]
                    - full["rmse"]
                ),

                "rmse_change_percent": (
                    (
                        row["rmse"]
                        - full["rmse"]
                    )
                    / full["rmse"]
                    * 100.0
                ),

                "smape": row["smape"],

                "r2": row["r2"],
            }
        )

    comparison_df = pd.DataFrame(
        comparison
    )

    comparison_file = (
        RESULT_DIR
        / "soh_feature_ablation_comparison.csv"
    )

    comparison_df.to_csv(
        comparison_file,
        index=False
    )

    print("\n" + "=" * 70)
    print("COMPARISON WITH FULL MODEL")
    print("=" * 70)

    print(
        comparison_df.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print(
        f"\nOverall:\n{overall_file}"
    )

    print(
        f"\nFolds:\n{fold_file}"
    )

    print(
        f"\nComparison:\n{comparison_file}"
    )

    print("\n" + "#" * 70)
    print("SOH FEATURE ABLATION COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()