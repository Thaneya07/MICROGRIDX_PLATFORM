from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "fault_detection"
    / "models"
)

MODEL_PATH = (
    MODEL_DIR
    / "fault_random_forest.joblib"
)

ENCODER_PATH = (
    MODEL_DIR
    / "fault_label_encoder.joblib"
)


# ============================================================
# LOAD MODELS
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Fault model not found: {MODEL_PATH}"
    )

if not ENCODER_PATH.exists():
    raise FileNotFoundError(
        f"Label encoder not found: {ENCODER_PATH}"
    )

FAULT_MODEL = joblib.load(MODEL_PATH)
LABEL_ENCODER = joblib.load(ENCODER_PATH)


# ============================================================
# FEATURES
# ============================================================

FEATURE_COLUMNS = [
    "EA",
    "EB",
    "EC",
]


# ============================================================
# FAULT INFORMATION
# ============================================================

FAULT_DESCRIPTIONS = {
    "Normal": "Normal operating condition.",
    "CS": "Capacitor switching event.",
    "HIF": "High impedance fault.",
    "LG": "Line-to-ground fault.",
    "LL": "Line-to-line fault.",
    "LLG": "Double line-to-ground fault.",
    "LLLG": "Three-phase-to-ground fault.",
    "LS": "Load switching event.",
}


# ============================================================
# PREDICTION
# ============================================================

def predict_fault(features: dict) -> dict:

    missing = [
        feature
        for feature in FEATURE_COLUMNS
        if feature not in features
    ]

    if missing:
        raise ValueError(
            f"Missing fault features: {missing}"
        )

    row = {
        feature: float(features[feature])
        for feature in FEATURE_COLUMNS
    }

    X = pd.DataFrame(
        [row],
        columns=FEATURE_COLUMNS,
    )

    prediction = FAULT_MODEL.predict(X)[0]

    predicted_class = LABEL_ENCODER.inverse_transform(
        [int(prediction)]
    )[0]

    # Random Forest class probabilities.
    probabilities = FAULT_MODEL.predict_proba(X)[0]

    confidence = float(
        np.max(probabilities) * 100.0
    )

    # --------------------------------------------------------
    # Operational status
    # --------------------------------------------------------

    if predicted_class == "Normal":
        system_status = "NORMAL"
        severity = "LOW"

    elif predicted_class in {"CS", "LS"}:
        system_status = "TRANSIENT_EVENT"
        severity = "MEDIUM"

    else:
        system_status = "FAULT_DETECTED"
        severity = "HIGH"

    description = FAULT_DESCRIPTIONS.get(
        predicted_class,
        "Unknown event.",
    )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    if predicted_class == "Normal":

        recommendation = (
            "Continue normal monitoring."
        )

    elif predicted_class in {"CS", "LS"}:

        recommendation = (
            "Monitor the transient event and "
            "verify system operating conditions."
        )

    else:

        recommendation = (
            "Investigate the affected electrical "
            "conditions and isolate the fault "
            "according to the protection strategy."
        )

    return {
        "fault_class": predicted_class,
        "description": description,
        "confidence_percent": round(
            confidence,
            3,
        ),
        "system_status": system_status,
        "severity": severity,
        "recommendation": recommendation,
        "model": "Random Forest",
    }