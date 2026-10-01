from pathlib import Path

import joblib
import numpy as np


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "battery_health"
    / "models"
)

SOH_MODEL_PATH = (
    MODEL_DIR
    / "soh_xgboost.joblib"
)

RUL_MODEL_PATH = (
    MODEL_DIR
    / "rul_xgboost.joblib"
)


# ============================================================
# FEATURES — MUST MATCH TRAINING ORDER
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


# ============================================================
# LOAD MODELS
# ============================================================

if not SOH_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"SOH model not found: {SOH_MODEL_PATH}"
    )

if not RUL_MODEL_PATH.exists():
    raise FileNotFoundError(
        f"RUL model not found: {RUL_MODEL_PATH}"
    )

SOH_MODEL = joblib.load(SOH_MODEL_PATH)
RUL_MODEL = joblib.load(RUL_MODEL_PATH)


# ============================================================
# MAIN PREDICTION
# ============================================================

def predict_battery_health(features: dict) -> dict:

    missing = [
        name
        for name in FEATURE_COLUMNS
        if name not in features
    ]

    if missing:
        raise ValueError(
            f"Missing battery-health features: {missing}"
        )

    # Keep exactly the same order as training.
    X = np.array(
        [[features[name] for name in FEATURE_COLUMNS]],
        dtype=float,
    )

    predicted_soh = float(
        SOH_MODEL.predict(X)[0]
    )

    predicted_rul = float(
        RUL_MODEL.predict(X)[0]
    )

    # Keep outputs physically sensible.
    predicted_soh = float(
        np.clip(predicted_soh, 0.0, 110.0)
    )

    predicted_rul = float(
        max(0.0, predicted_rul)
    )

    # ========================================================
    # DERIVED HEALTH INDICATORS
    # ========================================================

    temperature_max = float(
        features["temperature_max"]
    )

    temperature_mean = float(
        features["temperature_mean"]
    )

    # --------------------------------------------------------
    # Battery status
    # --------------------------------------------------------

    if predicted_soh >= 80.0:
        battery_status = "HEALTHY"
    elif predicted_soh >= 70.0:
        battery_status = "WARNING"
    else:
        battery_status = "CRITICAL"

    # --------------------------------------------------------
    # Risk score
    #
    # 0 = low risk
    # 100 = high risk
    #
    # This is an engineering-derived score, NOT a trained
    # probability model.
    # --------------------------------------------------------

    soh_risk = np.clip(
        (100.0 - predicted_soh) * 2.0,
        0.0,
        100.0,
    )

    rul_risk = np.clip(
        (40.0 - predicted_rul) / 40.0 * 100.0,
        0.0,
        100.0,
    )

    risk_score = float(
        0.60 * soh_risk
        + 0.40 * rul_risk
    )

    # --------------------------------------------------------
    # Failure probability
    #
    # Proxy risk estimate derived from health indicators.
    # It is NOT calibrated probabilistic ML output.
    # --------------------------------------------------------

    failure_probability = float(
        np.clip(
            risk_score,
            0.0,
            100.0,
        )
    )

    # --------------------------------------------------------
    # Thermal risk
    # --------------------------------------------------------

    if temperature_max >= 45.0:
        thermal_risk = "HIGH"
    elif temperature_max >= 40.0:
        thermal_risk = "MEDIUM"
    else:
        thermal_risk = "LOW"

    # --------------------------------------------------------
    # Efficiency score
    # --------------------------------------------------------

    efficiency_score = float(
        np.clip(
            (
                100.0
                - 0.6 * max(0.0, 100.0 - predicted_soh)
                - 0.4 * max(0.0, temperature_mean - 25.0) * 2.0
            ),
            0.0,
            100.0,
        )
    )

    # --------------------------------------------------------
    # Maintenance recommendation
    # --------------------------------------------------------

    if battery_status == "CRITICAL":

        maintenance_recommendation = (
            "Schedule battery inspection/replacement "
            "and avoid deep discharge."
        )

    elif thermal_risk == "HIGH":

        maintenance_recommendation = (
            "Check thermal conditions, cooling, and "
            "battery operating limits."
        )

    elif predicted_rul <= 20.0:

        maintenance_recommendation = (
            "Schedule preventive maintenance and "
            "prepare for battery replacement."
        )

    elif battery_status == "WARNING":

        maintenance_recommendation = (
            "Monitor battery degradation and "
            "schedule preventive inspection."
        )

    else:

        maintenance_recommendation = (
            "Battery condition is within the monitored "
            "operating range."
        )

    return {
        "soh_percent": round(
            predicted_soh,
            3,
        ),

        "rul_cycles": round(
            predicted_rul,
            3,
        ),

        "battery_status": battery_status,

        "risk_score": round(
            risk_score,
            3,
        ),

        "failure_probability_percent": round(
            failure_probability,
            3,
        ),

        "thermal_risk": thermal_risk,

        "efficiency_score": round(
            efficiency_score,
            3,
        ),

        "maintenance_recommendation": (
            maintenance_recommendation
        ),

        "model": {
            "soh": "XGBoost",
            "rul": "XGBoost",
        },
    }