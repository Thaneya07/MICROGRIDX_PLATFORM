from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
RAW_DIR = BASE_DIR / "datasets" / "solar" / "raw"

TRAIN_FILE = RAW_DIR / "train (1).csv"
TEST_FILE = RAW_DIR / "test (1).csv"

train = pd.read_csv(TRAIN_FILE)
test = pd.read_csv(TEST_FILE)

# Parse timestamps
train["timestamp"] = pd.to_datetime(train["timestamp"])
test["timestamp"] = pd.to_datetime(test["timestamp"])

print("=" * 70)
print("DKA SOLAR DATASET VALIDATION")
print("=" * 70)

# ---------------------------------------------------------
# 1. Timestamp information
# ---------------------------------------------------------
print("\nTIMESTAMP INFORMATION")
print("-" * 70)

print("Train start:", train["timestamp"].min())
print("Train end  :", train["timestamp"].max())
print("Test start :", test["timestamp"].min())
print("Test end   :", test["timestamp"].max())

train_diff = train["timestamp"].diff().dropna()
test_diff = test["timestamp"].diff().dropna()

print("\nTrain timestamp intervals:")
print(train_diff.value_counts().head(10))

print("\nTest timestamp intervals:")
print(test_diff.value_counts().head(10))

print("\nExpected interval: 5 minutes")

# ---------------------------------------------------------
# 2. Target analysis
# ---------------------------------------------------------
print("\nACTIVE POWER ANALYSIS")
print("-" * 70)

target = train["Active_Power"]

print("Minimum :", target.min())
print("Maximum :", target.max())
print("Mean    :", target.mean())
print("Median  :", target.median())
print("Std     :", target.std())

print("\nActive Power quantiles:")
print(target.quantile([0, .01, .05, .25, .50, .75, .95, .99, 1.0]))

print("\nNegative Active_Power values:", (target < 0).sum())
print("Zero Active_Power values    :", (target == 0).sum())

# ---------------------------------------------------------
# 3. Physical/range checks
# ---------------------------------------------------------
print("\nSUSPICIOUS VALUE CHECK")
print("-" * 70)

numeric_columns = train.select_dtypes(include=np.number).columns

for col in numeric_columns:
    s = train[col]

    print(f"\n{col}")
    print(f"  min       = {s.min():.6f}")
    print(f"  max       = {s.max():.6f}")
    print(f"  negative  = {(s < 0).sum():,}")
    print(f"  >99.9 pct = {(s > s.quantile(0.999)).sum():,}")

# ---------------------------------------------------------
# 4. Duplicate timestamps
# ---------------------------------------------------------
print("\nTIMESTAMP DUPLICATES")
print("-" * 70)

print("Train duplicate timestamps:", train["timestamp"].duplicated().sum())
print("Test duplicate timestamps :", test["timestamp"].duplicated().sum())

# ---------------------------------------------------------
# 5. Day/night target behavior
# ---------------------------------------------------------
print("\nACTIVE POWER BY HOUR")
print("-" * 70)

train["hour"] = train["timestamp"].dt.hour

hour_stats = train.groupby("hour")["Active_Power"].agg(
    ["count", "mean", "max"]
)

print(hour_stats.to_string())

# ---------------------------------------------------------
# 6. Final summary
# ---------------------------------------------------------
print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)