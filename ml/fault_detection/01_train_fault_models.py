from pathlib import Path
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from xgboost import XGBClassifier


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(
    r"C:\MicroGridX_PLATFORM\microgridx"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "datasets"
    / "fault_detection"
    / "raw"
    / "Fault_dataset.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "fault_detection"
    / "models"
)

RESULT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "fault_detection"
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
# DATA SETTINGS
# ============================================================

TARGET = "Class"

FEATURES = [
    "EA",
    "EB",
    "EC",
]

TEST_SIZE = 0.20
RANDOM_STATE = 42


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

    print("\n" + "=" * 70)
    print("DATASET INSPECTION")
    print("=" * 70)

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print(
        f"\nColumns:\n{list(df.columns)}"
    )

    required = FEATURES + [TARGET]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing)
        )

    # Keep only the required columns.
    df = df[
        required
    ].copy()

    # Convert numerical features.
    for feature in FEATURES:

        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )

    # Remove rows with missing data.
    before = len(df)

    df = df.dropna(
        subset=required
    ).reset_index(drop=True)

    removed = before - len(df)

    print(
        f"\nRows removed due to missing values: "
        f"{removed}"
    )

    print("\nClass distribution:")

    print(
        df[TARGET]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        f"\nNumber of classes: "
        f"{df[TARGET].nunique()}"
    )

    return df


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    y_true,
    y_pred,
):

    return {
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred
            )
        ),

        "precision_weighted": float(
            precision_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),

        "recall_weighted": float(
            recall_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),

        "f1_weighted": float(
            f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0,
            )
        ),
    }


# ============================================================
# MODELS
# ============================================================

def create_random_forest():

    return RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_leaf=1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def create_xgboost(
    num_classes,
):

    # XGBoost needs numeric encoded class labels.
    return XGBClassifier(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        objective=(
            "multi:softprob"
            if num_classes > 2
            else "binary:logistic"
        ),
        num_class=(
            num_classes
            if num_classes > 2
            else None
        ),
        eval_metric="mlogloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX FAULT DETECTION")
    print("#" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_data()

    X = df[
        FEATURES
    ]

    y_text = df[
        TARGET
    ].astype(str)

    # --------------------------------------------------------
    # Encode class labels
    # --------------------------------------------------------

    label_encoder = LabelEncoder()

    y = label_encoder.fit_transform(
        y_text
    )

    class_names = (
        label_encoder.classes_
        .tolist()
    )

    print("\nEncoded classes:")

    for index, name in enumerate(
        class_names
    ):

        print(
            f"{index}: {name}"
        )

    # --------------------------------------------------------
    # Stratified split
    # --------------------------------------------------------

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    )

    print("\n" + "=" * 70)
    print("TRAIN / TEST SPLIT")
    print("=" * 70)

    print(
        f"Training rows: {len(X_train)}"
    )

    print(
        f"Testing rows: {len(X_test)}"
    )

    # ========================================================
    # RANDOM FOREST
    # ========================================================

    print("\n" + "=" * 70)
    print("TRAINING RANDOM FOREST")
    print("=" * 70)

    rf = create_random_forest()

    rf.fit(
        X_train,
        y_train
    )

    rf_pred = rf.predict(
        X_test
    )

    rf_metrics = calculate_metrics(
        y_test,
        rf_pred
    )

    print("\nRandom Forest metrics:")

    for name, value in (
        rf_metrics.items()
    ):

        print(
            f"{name}: {value:.6f}"
        )

    print("\nRandom Forest classification report:")

    print(
        classification_report(
            y_test,
            rf_pred,
            target_names=class_names,
            zero_division=0,
        )
    )

    # ========================================================
    # XGBOOST
    # ========================================================

    print("\n" + "=" * 70)
    print("TRAINING XGBOOST")
    print("=" * 70)

    xgb = create_xgboost(
        len(class_names)
    )

    xgb.fit(
        X_train,
        y_train
    )

    xgb_pred = xgb.predict(
        X_test
    )

    xgb_pred = np.asarray(
        xgb_pred
    ).astype(int)

    xgb_metrics = calculate_metrics(
        y_test,
        xgb_pred
    )

    print("\nXGBoost metrics:")

    for name, value in (
        xgb_metrics.items()
    ):

        print(
            f"{name}: {value:.6f}"
        )

    print("\nXGBoost classification report:")

    print(
        classification_report(
            y_test,
            xgb_pred,
            target_names=class_names,
            zero_division=0,
        )
    )

    # ========================================================
    # CONFUSION MATRICES
    # ========================================================

    rf_cm = confusion_matrix(
        y_test,
        rf_pred,
        labels=np.arange(
            len(class_names)
        ),
    )

    xgb_cm = confusion_matrix(
        y_test,
        xgb_pred,
        labels=np.arange(
            len(class_names)
        ),
    )

    # --------------------------------------------------------
    # RF confusion matrix
    # --------------------------------------------------------

    plt.figure(
        figsize=(10, 8)
    )

    plt.imshow(
        rf_cm,
        interpolation="nearest"
    )

    plt.title(
        "Random Forest Confusion Matrix"
    )

    plt.xlabel(
        "Predicted Class"
    )

    plt.ylabel(
        "True Class"
    )

    plt.xticks(
        np.arange(len(class_names)),
        class_names,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        np.arange(len(class_names)),
        class_names
    )

    for i in range(
        rf_cm.shape[0]
    ):

        for j in range(
            rf_cm.shape[1]
        ):

            plt.text(
                j,
                i,
                str(rf_cm[i, j]),
                ha="center",
                va="center"
            )

    plt.tight_layout()

    rf_cm_file = (
        RESULT_DIR
        / "random_forest_confusion_matrix.png"
    )

    plt.savefig(
        rf_cm_file,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    # --------------------------------------------------------
    # XGB confusion matrix
    # --------------------------------------------------------

    plt.figure(
        figsize=(10, 8)
    )

    plt.imshow(
        xgb_cm,
        interpolation="nearest"
    )

    plt.title(
        "XGBoost Confusion Matrix"
    )

    plt.xlabel(
        "Predicted Class"
    )

    plt.ylabel(
        "True Class"
    )

    plt.xticks(
        np.arange(len(class_names)),
        class_names,
        rotation=45,
        ha="right"
    )

    plt.yticks(
        np.arange(len(class_names)),
        class_names
    )

    for i in range(
        xgb_cm.shape[0]
    ):

        for j in range(
            xgb_cm.shape[1]
        ):

            plt.text(
                j,
                i,
                str(xgb_cm[i, j]),
                ha="center",
                va="center"
            )

    plt.tight_layout()

    xgb_cm_file = (
        RESULT_DIR
        / "xgboost_confusion_matrix.png"
    )

    plt.savefig(
        xgb_cm_file,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    rf_importance = pd.DataFrame(
        {
            "feature": FEATURES,
            "importance": (
                rf.feature_importances_
            ),
        }
    ).sort_values(
        "importance",
        ascending=False
    )

    xgb_importance = pd.DataFrame(
        {
            "feature": FEATURES,
            "importance": (
                xgb.feature_importances_
            ),
        }
    ).sort_values(
        "importance",
        ascending=False
    )

    rf_importance_file = (
        RESULT_DIR
        / "random_forest_feature_importance.csv"
    )

    xgb_importance_file = (
        RESULT_DIR
        / "xgboost_feature_importance.csv"
    )

    rf_importance.to_csv(
        rf_importance_file,
        index=False
    )

    xgb_importance.to_csv(
        xgb_importance_file,
        index=False
    )

    print("\n" + "=" * 70)
    print("RANDOM FOREST FEATURE IMPORTANCE")
    print("=" * 70)

    print(
        rf_importance.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("XGBOOST FEATURE IMPORTANCE")
    print("=" * 70)

    print(
        xgb_importance.to_string(
            index=False
        )
    )

    # ========================================================
    # SAVE MODELS
    # ========================================================

    rf_model_file = (
        MODEL_DIR
        / "fault_random_forest.joblib"
    )

    xgb_model_file = (
        MODEL_DIR
        / "fault_xgboost.joblib"
    )

    encoder_file = (
        MODEL_DIR
        / "fault_label_encoder.joblib"
    )

    joblib.dump(
        rf,
        rf_model_file
    )

    joblib.dump(
        xgb,
        xgb_model_file
    )

    joblib.dump(
        label_encoder,
        encoder_file
    )

    # ========================================================
    # SAVE PREDICTIONS
    # ========================================================

    prediction_df = X_test.copy()

    prediction_df[
        "actual_class"
    ] = label_encoder.inverse_transform(
        y_test
    )

    prediction_df[
        "rf_predicted_class"
    ] = label_encoder.inverse_transform(
        rf_pred
    )

    prediction_df[
        "xgb_predicted_class"
    ] = label_encoder.inverse_transform(
        xgb_pred
    )

    prediction_file = (
        RESULT_DIR
        / "fault_test_predictions.csv"
    )

    prediction_df.to_csv(
        prediction_file,
        index=False
    )

    # ========================================================
    # SAVE SUMMARY
    # ========================================================

    summary = {
        "task": "Fault Detection",
        "dataset": str(INPUT_FILE),
        "rows": int(len(df)),
        "features": FEATURES,
        "target": TARGET,
        "classes": class_names,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "models": {
            "Random Forest": rf_metrics,
            "XGBoost": xgb_metrics,
        },
        "files": {
            "random_forest_model": str(
                rf_model_file
            ),
            "xgboost_model": str(
                xgb_model_file
            ),
            "label_encoder": str(
                encoder_file
            ),
            "predictions": str(
                prediction_file
            ),
            "rf_confusion_matrix": str(
                rf_cm_file
            ),
            "xgb_confusion_matrix": str(
                xgb_cm_file
            ),
        },
    }

    summary_file = (
        RESULT_DIR
        / "fault_detection_results.json"
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

    # ========================================================
    # FINAL COMPARISON
    # ========================================================

    comparison = pd.DataFrame(
        [
            {
                "model": "Random Forest",
                **rf_metrics,
            },
            {
                "model": "XGBoost",
                **xgb_metrics,
            },
        ]
    )

    comparison_file = (
        RESULT_DIR
        / "fault_model_comparison.csv"
    )

    comparison.to_csv(
        comparison_file,
        index=False
    )

    print("\n" + "=" * 70)
    print("FINAL MODEL COMPARISON")
    print("=" * 70)

    print(
        comparison.to_string(
            index=False
        )
    )

    print("\n" + "=" * 70)
    print("MODELS SAVED")
    print("=" * 70)

    print(rf_model_file)
    print(xgb_model_file)
    print(encoder_file)

    print("\n" + "=" * 70)
    print("RESULTS SAVED")
    print("=" * 70)

    print(comparison_file)
    print(summary_file)

    print("\n" + "#" * 70)
    print("FAULT DETECTION COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()