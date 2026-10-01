from pathlib import Path

import pandas as pd


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
    / "battery_health_targets.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "battery_health"
    / "processed"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MODEL FEATURES
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
# LOAD
# ============================================================

def load_dataset() -> pd.DataFrame:

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    print(
        f"Loaded rows: {len(df)}"
    )

    return df


# ============================================================
# VALIDATE FEATURES
# ============================================================

def validate_features(df: pd.DataFrame):

    required = (
        FEATURE_COLUMNS
        + [
            "battery_id",
            "cycle",
            "capacity_ah",
            "soh_percent",
            "rul_cycles",
            "rul_observed",
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

    feature_missing = (
        df[FEATURE_COLUMNS]
        .isna()
        .sum()
        .sum()
    )

    if feature_missing != 0:

        raise ValueError(
            f"Feature matrix contains "
            f"{feature_missing} missing values."
        )


# ============================================================
# CREATE SOH DATASET
# ============================================================

def create_soh_dataset(
    df: pd.DataFrame
) -> pd.DataFrame:

    columns = [
        "battery_id",
        "cycle",
    ] + FEATURE_COLUMNS + [
        "soh_percent",
    ]

    soh_df = df[columns].copy()

    soh_df = (
        soh_df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )

    return soh_df


# ============================================================
# CREATE RUL DATASET
# ============================================================

def create_rul_dataset(
    df: pd.DataFrame
) -> pd.DataFrame:

    # Only records with observed RUL are usable
    # for ordinary supervised regression.
    rul_df = df[
        df["rul_observed"]
    ].copy()

    columns = [
        "battery_id",
        "cycle",
    ] + FEATURE_COLUMNS + [
        "rul_cycles",
    ]

    rul_df = rul_df[columns]

    rul_df = (
        rul_df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )

    return rul_df


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX BATTERY ML DATASET PREPARATION")
    print("#" * 70)

    df = load_dataset()

    validate_features(df)

    # --------------------------------------------------------
    # SOH
    # --------------------------------------------------------

    soh_df = create_soh_dataset(df)

    soh_output = (
        OUTPUT_DIR
        / "battery_soh_ml.csv"
    )

    soh_df.to_csv(
        soh_output,
        index=False
    )

    # --------------------------------------------------------
    # RUL
    # --------------------------------------------------------

    rul_df = create_rul_dataset(df)

    rul_output = (
        OUTPUT_DIR
        / "battery_rul_ml.csv"
    )

    rul_df.to_csv(
        rul_output,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("SOH DATASET")
    print("=" * 70)

    print(
        f"Rows: {len(soh_df)}"
    )

    print(
        f"Features: {len(FEATURE_COLUMNS)}"
    )

    print(
        "\nRows by battery:"
    )

    print(
        soh_df
        .groupby("battery_id")
        .size()
        .to_string()
    )

    print(
        "\nSOH range:"
    )

    print(
        f"Minimum: "
        f"{soh_df['soh_percent'].min():.4f}%"
    )

    print(
        f"Maximum: "
        f"{soh_df['soh_percent'].max():.4f}%"
    )

    print("\n" + "=" * 70)
    print("RUL DATASET")
    print("=" * 70)

    print(
        f"Rows: {len(rul_df)}"
    )

    print(
        f"Features: {len(FEATURE_COLUMNS)}"
    )

    print(
        "\nRows by battery:"
    )

    print(
        rul_df
        .groupby("battery_id")
        .size()
        .to_string()
    )

    print(
        "\nRUL range:"
    )

    print(
        f"Minimum: "
        f"{rul_df['rul_cycles'].min():.0f} cycles"
    )

    print(
        f"Maximum: "
        f"{rul_df['rul_cycles'].max():.0f} cycles"
    )

    # --------------------------------------------------------
    # Save feature manifest
    # --------------------------------------------------------

    manifest_file = (
        OUTPUT_DIR
        / "battery_ml_features.txt"
    )

    with open(
        manifest_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "Battery Health ML Features\n"
        )

        f.write(
            "==========================\n\n"
        )

        for feature in FEATURE_COLUMNS:

            f.write(
                f"{feature}\n"
            )

        f.write(
            "\nSOH target: soh_percent\n"
        )

        f.write(
            "RUL target: rul_cycles\n"
        )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("PREPARATION COMPLETE")
    print("=" * 70)

    print(
        f"\nSOH dataset:\n{soh_output}"
    )

    print(
        f"\nRUL dataset:\n{rul_output}"
    )

    print(
        f"\nFeature manifest:\n{manifest_file}"
    )

    print("\nFirst 5 SOH records:")

    print(
        soh_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                "soh_percent",
            ]
        ]
        .head()
        .to_string(index=False)
    )

    print("\nFirst 5 RUL records:")

    print(
        rul_df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                "rul_cycles",
            ]
        ]
        .head()
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()