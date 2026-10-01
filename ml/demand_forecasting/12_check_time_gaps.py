from pathlib import Path
import pandas as pd

# ============================================================
# MicroGridX - Demand Forecasting
# Step 12: Diagnose Time Gaps
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
)

FILES = {
    "Training": DATA_DIR / "enhanced_train.csv",
    "Validation": DATA_DIR / "enhanced_validation.csv",
    "Test": DATA_DIR / "enhanced_test.csv",
}

EXPECTED_INTERVAL = pd.Timedelta(minutes=30)

print("=" * 70)
print("MicroGridX - Time Gap Diagnosis")
print("=" * 70)

total_gaps = 0

for name, path in FILES.items():

    print("\n" + "-" * 70)
    print(name)
    print("-" * 70)

    df = pd.read_csv(path)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    df = df.sort_values("timestamp")

    differences = (
        df["timestamp"]
        .diff()
        .dropna()
    )

    gap_mask = (
        differences != EXPECTED_INTERVAL
    )

    gap_positions = differences[
        gap_mask
    ]

    print(
        f"Unexpected gaps: "
        f"{len(gap_positions)}"
    )

    for position, difference in gap_positions.items():

        previous_timestamp = df.loc[
            position - 1,
            "timestamp"
        ]

        current_timestamp = df.loc[
            position,
            "timestamp"
        ]

        missing_intervals = (
            int(
                difference
                / EXPECTED_INTERVAL
            )
            - 1
        )

        print(
            f"\nPrevious : {previous_timestamp}"
        )

        print(
            f"Current  : {current_timestamp}"
        )

        print(
            f"Gap      : {difference}"
        )

        print(
            f"Missing 30-min intervals: "
            f"{missing_intervals}"
        )

        total_gaps += 1


print("\n" + "=" * 70)
print(
    f"TOTAL UNEXPECTED GAPS: {total_gaps}"
)
print("=" * 70)