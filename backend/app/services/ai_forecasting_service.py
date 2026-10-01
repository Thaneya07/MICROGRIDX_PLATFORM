from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_DIR = PROJECT_ROOT / "ml"

DATA_DIR = PROJECT_ROOT / "datasets"

DEMAND_MODEL_PATH = (
    MODEL_DIR
    / "demand_forecasting"
    / "models"
    / "enhanced_random_forest.joblib"
)

SOLAR_MODEL_PATH = (
    MODEL_DIR
    / "solar_forecasting"
    / "models"
    / "solar_random_forest_baseline.joblib"
)

DEMAND_DATA_PATH = (
    DATA_DIR
    / "demand"
    / "processed"
    / "demand_enhanced_features.csv"
)

SOLAR_DATA_PATH = (
    DATA_DIR
    / "solar"
    / "processed"
    / "solar_features.csv"
)


# ============================================================
# LOAD MODELS
# ============================================================

if not DEMAND_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Demand model not found: {DEMAND_MODEL_PATH}"
    )

if not SOLAR_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Solar model not found: {SOLAR_MODEL_PATH}"
    )


DEMAND_MODEL = joblib.load(DEMAND_MODEL_PATH)
SOLAR_MODEL = joblib.load(SOLAR_MODEL_PATH)


# ============================================================
# FEATURE NAMES
# ============================================================

DEMAND_FEATURES = list(
    getattr(DEMAND_MODEL, "feature_names_in_", [])
)

SOLAR_FEATURES = list(
    getattr(SOLAR_MODEL, "feature_names_in_", [])
)


# ============================================================
# BASIC PREDICTION
# ============================================================

def _predict(
    model,
    required_features,
    features,
):
    if not required_features:
        raise RuntimeError(
            "Model does not expose feature_names_in_."
        )

    missing = [
        name
        for name in required_features
        if name not in features
    ]

    if missing:
        raise ValueError(
            f"Missing features: {missing}"
        )

    row = {
        name: float(features[name])
        for name in required_features
    }

    X = pd.DataFrame(
        [row],
        columns=required_features,
    )

    prediction = float(
        model.predict(X)[0]
    )

    return prediction


# ============================================================
# RANDOM FOREST UNCERTAINTY
# ============================================================

def _random_forest_interval(
    model,
    X: pd.DataFrame,
    prediction_scale: float = 1.0,
):
    """
    Estimate an empirical interval from the individual
    Random Forest tree predictions.

    This is an uncertainty spread from the ensemble.
    It is not a calibrated statistical confidence interval.
    """

    if not hasattr(model, "estimators_"):
        prediction = float(model.predict(X)[0])
        return prediction, prediction, prediction

    tree_predictions = np.asarray(
        [
            estimator.predict(X)[0]
            for estimator in model.estimators_
        ],
        dtype=float,
    )

    prediction = float(
        model.predict(X)[0]
    )

    std = float(
        np.std(tree_predictions)
    )

    lower = prediction - (1.96 * std)
    upper = prediction + (1.96 * std)

    return (
        prediction * prediction_scale,
        max(0.0, lower * prediction_scale),
        max(0.0, upper * prediction_scale),
    )


# ============================================================
# DEMAND
# ============================================================

def predict_demand(features: dict) -> dict:

    prediction_w = _predict(
        DEMAND_MODEL,
        DEMAND_FEATURES,
        features,
    )

    return {
        "prediction_w": round(
            prediction_w,
            3,
        ),
        "unit": "W",
        "model": "Enhanced Random Forest",
        "feature_count": len(
            DEMAND_FEATURES
        ),
    }


# ============================================================
# SOLAR
# ============================================================

def predict_solar(features: dict) -> dict:

    # Active_Power in the solar training dataset/model
    # is represented in kW.
    prediction_kw = _predict(
        SOLAR_MODEL,
        SOLAR_FEATURES,
        features,
    )

    prediction_w = prediction_kw * 1000.0

    return {
        "prediction_w": round(
            max(0.0, prediction_w),
            3,
        ),
        "unit": "W",
        "model": "Random Forest",
        "feature_count": len(
            SOLAR_FEATURES
        ),
        "training_target_unit": "kW",
    }


# ============================================================
# HISTORICAL MODEL REPLAY
# ============================================================

def _build_replay(
    model,
    data_path: Path,
    required_features,
    target_name: str,
    points: int,
    target_scale: float = 1.0,
    model_name: str = "",
):
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {data_path}"
        )

    df = pd.read_csv(data_path)

    if "timestamp" not in df.columns:
        raise ValueError(
            f"{data_path.name} does not contain a timestamp column."
        )

    missing = [
        name
        for name in required_features
        if name not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{data_path.name} is missing model features: {missing}"
        )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df = df.dropna(
        subset=["timestamp"]
    )

    df = df.dropna(
        subset=required_features
    )

    df = df.sort_values(
        "timestamp"
    )

    points = max(
        1,
        min(
            int(points),
            len(df),
        ),
    )

    selected = df.tail(points).copy()

    X = selected[
        required_features
    ].astype(float)

    predictions = model.predict(X)

    result_points = []

    # Random Forest tree predictions for uncertainty.
    tree_matrix = None

    if hasattr(model, "estimators_"):
        tree_matrix = np.asarray(
            [
                estimator.predict(X)
                for estimator in model.estimators_
            ],
            dtype=float,
        )

    for idx, (_, row) in enumerate(
        selected.iterrows()
    ):
        prediction = float(
            predictions[idx]
        )

        if tree_matrix is not None:
            tree_values = tree_matrix[:, idx]

            std = float(
                np.std(tree_values)
            )

            lower = prediction - (
                1.96 * std
            )

            upper = prediction + (
                1.96 * std
            )
        else:
            lower = prediction
            upper = prediction

        prediction *= target_scale
        lower *= target_scale
        upper *= target_scale

        result_points.append(
            {
                "timestamp": row[
                    "timestamp"
                ].isoformat(),

                "predicted_w": round(
                    max(
                        0.0,
                        prediction,
                    ),
                    3,
                ),

                "lower_95_w": round(
                    max(
                        0.0,
                        lower,
                    ),
                    3,
                ),

                "upper_95_w": round(
                    max(
                        0.0,
                        upper,
                    ),
                    3,
                ),
            }
        )

    if not result_points:
        raise ValueError(
            f"No usable rows available in {data_path.name}."
        )

    return {
        "target": target_name,
        "model": model_name,
        "points": result_points,
        "data_provenance_note": (
            "Historical model replay using prepared public "
            "dataset feature rows and the saved trained model. "
            "This is not live telemetry and does not represent "
            "a forecast of future measurements. Ensemble spread "
            "is shown as an uncertainty indicator, not a calibrated "
            "confidence interval."
        ),
    }


def replay_demand(
    points: int = 24,
):
    return _build_replay(
        model=DEMAND_MODEL,
        data_path=DEMAND_DATA_PATH,
        required_features=DEMAND_FEATURES,
        target_name="DEMAND",
        points=points,
        target_scale=1.0,
        model_name="Enhanced Random Forest",
    )


def replay_solar(
    points: int = 144,
):
    return _build_replay(
        model=SOLAR_MODEL,
        data_path=SOLAR_DATA_PATH,
        required_features=SOLAR_FEATURES,
        target_name="SOLAR_GENERATION",
        points=points,
        target_scale=1000.0,
        model_name="Random Forest",
    )


# ============================================================
# MODEL INFORMATION
# ============================================================

def get_model_info():

    return {
        "demand": {
            "model": "Enhanced Random Forest",
            "feature_count": len(
                DEMAND_FEATURES
            ),
            "features": DEMAND_FEATURES,
        },
        "solar": {
            "model": "Random Forest",
            "feature_count": len(
                SOLAR_FEATURES
            ),
            "features": SOLAR_FEATURES,
        },
    }