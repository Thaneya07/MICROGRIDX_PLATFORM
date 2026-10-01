from pathlib import Path

import numpy as np
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
    / "battery_discharge_features.csv"
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

OUTPUT_FILE = (
    OUTPUT_DIR
    / "battery_health_targets.csv"
)


# ============================================================
# BATTERY HEALTH DEFINITIONS
# ============================================================

# NASA battery nominal/rated capacity
NOMINAL_CAPACITY_AH = 2.0

# NASA dataset EOL criterion:
# 30% capacity fade from 2 Ah
EOL_CAPACITY_AH = 1.4


# ============================================================
# LOAD DATA
# ============================================================

def load_data() -> pd.DataFrame:

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    if df.empty:

        raise ValueError(
            "Input dataset is empty."
        )

    required_columns = [
        "battery_id",
        "cycle",
        "discharge_cycle_index",
        "capacity_ah",
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    return df


# ============================================================
# CREATE SOH
# ============================================================

def create_soh(df: pd.DataFrame) -> pd.DataFrame:

    # --------------------------------------------------------
    # State of Health
    #
    # SOH (%) = measured capacity / nominal capacity * 100
    # --------------------------------------------------------

    df["nominal_capacity_ah"] = NOMINAL_CAPACITY_AH

    df["soh_percent"] = (
        df["capacity_ah"]
        / NOMINAL_CAPACITY_AH
        * 100.0
    )

    # Capacity fade relative to nominal capacity
    df["capacity_fade_percent"] = (
        100.0
        - df["soh_percent"]
    )

    return df


# ============================================================
# CREATE RUL
# ============================================================

def create_rul(df: pd.DataFrame) -> pd.DataFrame:

    # Initialize columns
    df["eol_capacity_ah"] = EOL_CAPACITY_AH

    df["eol_reached"] = False

    df["eol_discharge_cycle_index"] = np.nan

    df["eol_experiment_cycle"] = np.nan

    df["rul_cycles"] = np.nan

    df["rul_observed"] = False

    # --------------------------------------------------------
    # Process each battery independently
    # --------------------------------------------------------

    for battery_id, group in df.groupby(
        "battery_id",
        sort=False
    ):

        group = (
            group
            .sort_values(
                "discharge_cycle_index"
            )
        )

        # ----------------------------------------------------
        # Find first cycle at or below EOL threshold
        # ----------------------------------------------------

        eol_rows = group[
            group["capacity_ah"]
            <= EOL_CAPACITY_AH
        ]

        # ----------------------------------------------------
        # Battery reached EOL
        # ----------------------------------------------------

        if not eol_rows.empty:

            first_eol = eol_rows.iloc[0]

            eol_discharge_index = int(
                first_eol[
                    "discharge_cycle_index"
                ]
            )

            eol_experiment_cycle = int(
                first_eol["cycle"]
            )

            # -----------------------------------------------
            # Mark EOL cycle
            # -----------------------------------------------

            battery_mask = (
                df["battery_id"]
                == battery_id
            )

            df.loc[
                battery_mask,
                "eol_discharge_cycle_index"
            ] = eol_discharge_index

            df.loc[
                battery_mask,
                "eol_experiment_cycle"
            ] = eol_experiment_cycle

            # -----------------------------------------------
            # Calculate RUL
            #
            # RUL is measured in remaining DISCHARGE cycles.
            # -----------------------------------------------

            before_eol = (
                battery_mask
                &
                (
                    df["discharge_cycle_index"]
                    <= eol_discharge_index
                )
            )

            df.loc[
                before_eol,
                "rul_cycles"
            ] = (
                eol_discharge_index
                - df.loc[
                    before_eol,
                    "discharge_cycle_index"
                ]
            )

            df.loc[
                before_eol,
                "rul_observed"
            ] = True

            # -----------------------------------------------
            # Identify individual EOL record
            # -----------------------------------------------

            eol_mask = (
                battery_mask
                &
                (
                    df["discharge_cycle_index"]
                    == eol_discharge_index
                )
            )

            df.loc[
                eol_mask,
                "eol_reached"
            ] = True

        # ----------------------------------------------------
        # Battery did not reach EOL
        # ----------------------------------------------------

        else:

            # No fabricated RUL.
            #
            # The battery is right-censored at the end of
            # the available experiment.

            print(
                f"\nINFO: {battery_id} did not reach "
                f"the {EOL_CAPACITY_AH:.1f} Ah EOL threshold."
            )

    return df


# ============================================================
# VALIDATE TARGETS
# ============================================================

def validate_targets(df: pd.DataFrame):

    print("\n" + "=" * 70)
    print("TARGET VALIDATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    print("\nMissing values in target columns:")

    target_columns = [
        "soh_percent",
        "capacity_fade_percent",
        "eol_discharge_cycle_index",
        "eol_experiment_cycle",
        "rul_cycles",
    ]

    print(
        df[target_columns]
        .isna()
        .sum()
        .to_string()
    )

    # --------------------------------------------------------
    # SOH summary
    # --------------------------------------------------------

    print("\nSOH summary by battery:")

    soh_summary = (
        df.groupby("battery_id")[
            "soh_percent"
        ]
        .agg(
            [
                "count",
                "min",
                "max",
                "mean",
                "std",
            ]
        )
    )

    print(
        soh_summary.to_string()
    )

    # --------------------------------------------------------
    # RUL / EOL summary
    # --------------------------------------------------------

    print("\nEOL/RUL summary:")

    for battery_id, group in df.groupby(
        "battery_id",
        sort=False
    ):

        eol_indices = group[
            "eol_discharge_cycle_index"
        ].dropna()

        if eol_indices.empty:

            print(
                f"{battery_id}: "
                "EOL not observed "
                f"(capacity remained above "
                f"{EOL_CAPACITY_AH:.1f} Ah)"
            )

        else:

            eol_index = int(
                eol_indices.iloc[0]
            )

            eol_rows = group[
                group[
                    "discharge_cycle_index"
                ] == eol_index
            ]

            eol_capacity = float(
                eol_rows[
                    "capacity_ah"
                ].iloc[0]
            )

            print(
                f"{battery_id}: "
                f"EOL discharge index = "
                f"{eol_index}, "
                f"EOL experiment cycle = "
                f"{int(eol_rows['cycle'].iloc[0])}, "
                f"EOL capacity = "
                f"{eol_capacity:.6f} Ah"
            )

    # --------------------------------------------------------
    # RUL range
    # --------------------------------------------------------

    observed_rul = df.loc[
        df["rul_observed"],
        "rul_cycles"
    ]

    if not observed_rul.empty:

        print("\nObserved RUL range:")

        print(
            f"Minimum RUL: "
            f"{observed_rul.min():.0f} discharge cycles"
        )

        print(
            f"Maximum RUL: "
            f"{observed_rul.max():.0f} discharge cycles"
        )

    # --------------------------------------------------------
    # Check for negative RUL
    # --------------------------------------------------------

    negative_rul = (
        df["rul_cycles"].notna()
        &
        (
            df["rul_cycles"] < 0
        )
    ).sum()

    print(
        f"\nNegative RUL records: "
        f"{negative_rul}"
    )

    if negative_rul != 0:

        raise ValueError(
            "Negative RUL values detected."
        )

    # --------------------------------------------------------
    # Check monotonic relationship at EOL
    # --------------------------------------------------------

    eol_records = df[
        df["eol_reached"]
    ]

    if not eol_records.empty:

        print("\nEOL records:")

        print(
            eol_records[
                [
                    "battery_id",
                    "cycle",
                    "discharge_cycle_index",
                    "capacity_ah",
                    "soh_percent",
                    "rul_cycles",
                ]
            ]
            .to_string(index=False)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("MICROGRIDX BATTERY HEALTH TARGET CREATION")
    print("#" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    df = load_data()

    print(
        f"\nInput rows: {len(df)}"
    )

    print(
        f"Batteries: "
        f"{df['battery_id'].nunique()}"
    )

    # --------------------------------------------------------
    # Sort first
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Create SOH
    # --------------------------------------------------------

    df = create_soh(df)

    # --------------------------------------------------------
    # Create RUL
    # --------------------------------------------------------

    df = create_rul(df)

    # --------------------------------------------------------
    # Reorder important columns
    # --------------------------------------------------------

    first_columns = [
        "battery_id",
        "cycle",
        "discharge_cycle_index",
        "ambient_temperature",

        "capacity_ah",
        "nominal_capacity_ah",

        "soh_percent",
        "capacity_fade_percent",

        "eol_capacity_ah",
        "eol_reached",
        "eol_discharge_cycle_index",
        "eol_experiment_cycle",

        "rul_cycles",
        "rul_observed",
    ]

    remaining_columns = [
        col
        for col in df.columns
        if col not in first_columns
    ]

    df = df[
        first_columns
        + remaining_columns
    ]

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_targets(df)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TARGET CREATION COMPLETE")
    print("=" * 70)

    print(
        f"\nOutput file:\n{OUTPUT_FILE}"
    )

    print(
        f"\nRows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print("\nFirst 10 target records:")

    print(
        df[
            [
                "battery_id",
                "cycle",
                "discharge_cycle_index",
                "capacity_ah",
                "soh_percent",
                "rul_cycles",
                "rul_observed",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()