from pathlib import Path
import pandas as pd

# ============================================================
# MicroGridX - Demand Forecasting
# Step 8: Enhanced Chronological Train / Validation / Test Split
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
    / "demand_enhanced_features.csv"
)

OUTPUT_DIR = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
)

TRAIN_PATH = OUTPUT_DIR / "enhanced_train.csv"
VAL_PATH = OUTPUT_DIR / "enhanced_validation.csv"
TEST_PATH = OUTPUT_DIR / "enhanced_test.csv"

print("=" * 70)
print("MicroGridX - Enhanced Chronological Dataset Split")
print("=" * 70)

# ------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------

df = pd.read_csv(INPUT_PATH)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = (
    df.sort_values("timestamp")
    .reset_index(drop=True)
)

print(f"\nTotal observations: {len(df):,}")

# ------------------------------------------------------------
# Split
# ------------------------------------------------------------

train_ratio = 0.70
validation_ratio = 0.15

n = len(df)

train_end = int(n * train_ratio)

validation_end = int(
    n * (train_ratio + validation_ratio)
)

train = df.iloc[:train_end].copy()

validation = df.iloc[
    train_end:validation_end
].copy()

test = df.iloc[
    validation_end:
].copy()

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

train.to_csv(
    TRAIN_PATH,
    index=False
)

validation.to_csv(
    VAL_PATH,
    index=False
)

test.to_csv(
    TEST_PATH,
    index=False
)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("SPLIT SUMMARY")
print("=" * 70)

print(
    f"\nTraining observations   : {len(train):,}"
    f"\nValidation observations : {len(validation):,}"
    f"\nTest observations       : {len(test):,}"
)

print("\nPercentages:")

print(f"Training   : {len(train) / n * 100:.2f}%")
print(f"Validation : {len(validation) / n * 100:.2f}%")
print(f"Test       : {len(test) / n * 100:.2f}%")

print("\nTime ranges:")

print(
    f"\nTraining:"
    f"\n  Start: {train['timestamp'].min()}"
    f"\n  End  : {train['timestamp'].max()}"
)

print(
    f"\nValidation:"
    f"\n  Start: {validation['timestamp'].min()}"
    f"\n  End  : {validation['timestamp'].max()}"
)

print(
    f"\nTest:"
    f"\n  Start: {test['timestamp'].min()}"
    f"\n  End  : {test['timestamp'].max()}"
)

# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

assert (
    train["timestamp"].max()
    < validation["timestamp"].min()
)

assert (
    validation["timestamp"].max()
    < test["timestamp"].min()
)

print("\nChronological ordering check: PASSED")

print("\nDuplicate timestamps:")

print(
    f"Training   : "
    f"{train['timestamp'].duplicated().sum()}"
)

print(
    f"Validation : "
    f"{validation['timestamp'].duplicated().sum()}"
)

print(
    f"Test       : "
    f"{test['timestamp'].duplicated().sum()}"
)

print("\nSaved files:")

print(TRAIN_PATH)
print(VAL_PATH)
print(TEST_PATH)

print("\nEnhanced dataset splitting complete.")