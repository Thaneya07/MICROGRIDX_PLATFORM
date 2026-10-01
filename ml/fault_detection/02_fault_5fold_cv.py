from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import StratifiedKFold
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

RESULT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "fault_detection"
    / "results"
)

RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

FEATURES = [
    "EA",
    "EB",
    "EC",
]

TARGET = "Class"

N_SPLITS = 5
RANDOM_STATE = 42


# ============================================================
# MODELS
# ============================================================

def create_rf():

    return RandomForestClassifier(
        n_estimators=300,
        max_depth=20,
        min_samples_leaf=1,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def create_xgb(num_classes):

    return XGBClassifier(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        objective="multi:softprob",
        num_class=num_classes,
        eval_metric="mlogloss",
        random_state=RANDOM_STATE,
        n_jobs=-1,
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

    df = df[
        FEATURES + [TARGET]
    ].copy()

    for feature in FEATURES:
        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )

    df = df.dropna(
        subset=FEATURES + [TARGET]
    ).reset_index(drop=True)

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

        "precision_macro": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0
            )
        ),

        "recall_macro": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0
            )
        ),

        "f1_macro": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0
            )
        ),

        "precision_weighted": float(
            precision_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            )
        ),

        "recall_weighted": float(
            recall_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            )
        ),

        "f1_weighted": float(
            f1_score(
                y_true,
                y_pred,
                average="weighted",
                zero_division=0
            )
        ),
    }


# ============================================================
# RUN 5-FOLD CV
# ============================================================

def run_cv(
    X,
    y,
    class_names,
    model_name,
    model_factory,
):

    skf = StratifiedKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE,
    )

    fold_results = []

    all_true = []
    all_pred = []

    print("\n" + "=" * 70)
    print(
        f"{model_name.upper()} — "
        f"{N_SPLITS}-FOLD STRATIFIED CV"
    )
    print("=" * 70)

    for fold, (train_idx, test_idx) in enumerate(
        skf.split(X, y),
        start=1
    ):

        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y[train_idx]
        y_test = y[test_idx]

        model = model_factory()

        model.fit(
            X_train,
            y_train
        )

        y_pred = model.predict(
            X_test
        )

        fold_metrics = calculate_metrics(
            y_test,
            y_pred
        )

        fold_metrics["model"] = model_name
        fold_metrics["fold"] = fold
        fold_metrics["train_rows"] = len(
            train_idx
        )
        fold_metrics["test_rows"] = len(
            test_idx
        )

        fold_results.append(
            fold_metrics
        )

        all_true.extend(
            y_test.tolist()
        )

        all_pred.extend(
            np.asarray(y_pred).tolist()
        )

        print(
            f"\nFold {fold}"
        )

        print(
            f"Accuracy: "
            f"{fold_metrics['accuracy']:.6f}"
        )

        print(
            f"Macro Precision: "
            f"{fold_metrics['precision_macro']:.6f}"
        )

        print(
            f"Macro Recall: "
            f"{fold_metrics['recall_macro']:.6f}"
        )

        print(
            f"Macro F1: "
            f"{fold_metrics['f1_macro']:.6f}"
        )

    # --------------------------------------------------------
    # Aggregate OOF metrics
    # --------------------------------------------------------

    all_true = np.asarray(
        all_true
    )

    all_pred = np.asarray(
        all_pred
    )

    overall_metrics = calculate_metrics(
        all_true,
        all_pred
    )

    # --------------------------------------------------------
    # Mean and standard deviation across folds
    # --------------------------------------------------------

    fold_df = pd.DataFrame(
        fold_results
    )

    metric_names = [
        "accuracy",
        "precision_macro",
        "recall_macro",
        "f1_macro",
        "precision_weighted",
        "recall_weighted",
        "f1_weighted",
    ]

    summary = {
        "model": model_name
    }

    for metric in metric_names:

        summary[
            f"{metric}_mean"
        ] = float(
            fold_df[metric].mean()
        )

        summary[
            f"{metric}_std"
        ] = float(
            fold_df[metric].std(
                ddof=1
            )
        )

    # --------------------------------------------------------
    # OOF confusion matrix
    # --------------------------------------------------------

    cm = confusion_matrix(
        all_true,
        all_pred,
        labels=np.arange(
            len(class_names)
        )
    )

    # --------------------------------------------------------
    # Classification report
    # --------------------------------------------------------

    report = classification_report(
        all_true,
        all_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    return (
        fold_df,
        summary,
        overall_metrics,
        cm,
        report,
        all_true,
        all_pred,
    )


# ============================================================
# SAVE CONFUSION MATRIX
# ============================================================

def save_confusion_matrix(
    cm,
    class_names,
    model_name,
):

    output = pd.DataFrame(
        cm,
        index=class_names,
        columns=class_names
    )

    filename = (
        model_name.lower()
        .replace(" ", "_")
        + "_5fold_oof_confusion_matrix.csv"
    )

    path = RESULT_DIR / filename

    output.to_csv(path)

    return path


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX FAULT DETECTION — 5-FOLD VALIDATION")
    print("#" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_data()

    print(
        f"\nRows: {len(df)}"
    )

    print(
        f"Features: {FEATURES}"
    )

    print(
        "\nClass distribution:"
    )

    print(
        df[TARGET]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # Encode
    # --------------------------------------------------------

    encoder = LabelEncoder()

    y = encoder.fit_transform(
        df[TARGET].astype(str)
    )

    class_names = (
        encoder.classes_
        .tolist()
    )

    X = df[
        FEATURES
    ]

    print(
        "\nClasses:"
    )

    for i, name in enumerate(
        class_names
    ):
        print(
            f"{i}: {name}"
        )

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    (
        rf_folds,
        rf_summary,
        rf_oof,
        rf_cm,
        rf_report,
        rf_true,
        rf_pred,
    ) = run_cv(
        X,
        y,
        class_names,
        "Random Forest",
        create_rf,
    )

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    (
        xgb_folds,
        xgb_summary,
        xgb_oof,
        xgb_cm,
        xgb_report,
        xgb_true,
        xgb_pred,
    ) = run_cv(
        X,
        y,
        class_names,
        "XGBoost",
        lambda: create_xgb(
            len(class_names)
        ),
    )

    # ========================================================
    # FOLD RESULTS
    # ========================================================

    all_folds = pd.concat(
        [
            rf_folds,
            xgb_folds,
        ],
        ignore_index=True
    )

    fold_file = (
        RESULT_DIR
        / "fault_5fold_cv_results.csv"
    )

    all_folds.to_csv(
        fold_file,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary_df = pd.DataFrame(
        [
            rf_summary,
            xgb_summary,
        ]
    )

    summary_file = (
        RESULT_DIR
        / "fault_5fold_cv_summary.csv"
    )

    summary_df.to_csv(
        summary_file,
        index=False
    )

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    print("\n" + "=" * 70)
    print("5-FOLD CROSS-VALIDATION SUMMARY")
    print("=" * 70)

    print(
        summary_df.to_string(
            index=False
        )
    )

    # ========================================================
    # OOF RESULTS
    # ========================================================

    print("\n" + "=" * 70)
    print("POOLED OUT-OF-FOLD RESULTS")
    print("=" * 70)

    pooled_df = pd.DataFrame(
        [
            {
                "model": "Random Forest",
                **rf_oof,
            },
            {
                "model": "XGBoost",
                **xgb_oof,
            },
        ]
    )

    print(
        pooled_df.to_string(
            index=False
        )
    )

    pooled_file = (
        RESULT_DIR
        / "fault_5fold_pooled_results.csv"
    )

    pooled_df.to_csv(
        pooled_file,
        index=False
    )

    # ========================================================
    # CONFUSION MATRICES
    # ========================================================

    rf_cm_file = save_confusion_matrix(
        rf_cm,
        class_names,
        "Random Forest"
    )

    xgb_cm_file = save_confusion_matrix(
        xgb_cm,
        class_names,
        "XGBoost"
    )

    # ========================================================
    # CLASSIFICATION REPORTS
    # ========================================================

    rf_report_df = pd.DataFrame(
        rf_report
    ).transpose()

    xgb_report_df = pd.DataFrame(
        xgb_report
    ).transpose()

    rf_report_file = (
        RESULT_DIR
        / "fault_random_forest_5fold_report.csv"
    )

    xgb_report_file = (
        RESULT_DIR
        / "fault_xgboost_5fold_report.csv"
    )

    rf_report_df.to_csv(
        rf_report_file
    )

    xgb_report_df.to_csv(
        xgb_report_file
    )

    # ========================================================
    # JSON SUMMARY
    # ========================================================

    json_summary = {
        "task": "Fault Detection",
        "dataset": str(INPUT_FILE),
        "rows": int(len(df)),
        "features": FEATURES,
        "classes": class_names,
        "n_splits": N_SPLITS,
        "random_state": RANDOM_STATE,

        "random_forest": {
            "fold_mean": rf_summary,
            "pooled_oof": rf_oof,
        },

        "xgboost": {
            "fold_mean": xgb_summary,
            "pooled_oof": xgb_oof,
        },
    }

    json_file = (
        RESULT_DIR
        / "fault_5fold_cv_results.json"
    )

    with open(
        json_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            json_summary,
            f,
            indent=2
        )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("FILES SAVED")
    print("=" * 70)

    print(
        f"\nFold results:\n{fold_file}"
    )

    print(
        f"\nSummary:\n{summary_file}"
    )

    print(
        f"\nPooled results:\n{pooled_file}"
    )

    print(
        f"\nRF confusion matrix:\n{rf_cm_file}"
    )

    print(
        f"\nXGBoost confusion matrix:\n{xgb_cm_file}"
    )

    print(
        f"\nJSON:\n{json_file}"
    )

    print("\n" + "#" * 70)
    print("5-FOLD FAULT VALIDATION COMPLETE")
    print("#" * 70)


if __name__ == "__main__":
    main()