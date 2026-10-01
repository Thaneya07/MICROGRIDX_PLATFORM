from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# MicroGridX - Demand Forecasting
# Step 3: Leakage-Safe Feature Engineering
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
    / "demand_30min.csv"
)

OUTPUT_PATH = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
    / "demand_features.csv"
)

print("=" * 70)
print("MicroGridX Demand Forecasting - Feature Engineering")
print("=" * 70)

# ------------------------------------------------------------
# Load processed dataset
# ------------------------------------------------------------

print("\nLoading processed dataset...")

df = pd.read_csv(INPUT_PATH)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values("timestamp").reset_index(drop=True)

print(f"Input rows: {len(df):,}")

# ------------------------------------------------------------
# Calendar features
# ------------------------------------------------------------

print("\nCreating calendar features...")

df["hour_sin"] = np.sin(
    2 * np.pi * df["timestamp"].dt.hour / 24
)

df["hour_cos"] = np.cos(
    2 * np.pi * df["timestamp"].dt.hour / 24
)

df["day_of_week_sin"] = np.sin(
    2 * np.pi * df["timestamp"].dt.dayofweek / 7
)

df["day_of_week_cos"] = np.cos(
    2 * np.pi * df["timestamp"].dt.dayofweek / 7
)

df["month_sin"] = np.sin(
    2 * np.pi * (df["timestamp"].dt.month - 1) / 12
)

df["month_cos"] = np.cos(
    2 * np.pi * (df["timestamp"].dt.month - 1) / 12
)

df["is_weekend"] = (
    df["timestamp"].dt.dayofweek >= 5
).astype(int)

# ------------------------------------------------------------
# Historical lag features
# ------------------------------------------------------------

print("Creating historical lag features...")

# At 30-minute resolution:
#
# lag_1  = previous 30 minutes
# lag_2  = previous 1 hour
# lag_3  = previous 1.5 hours
# lag_48 = previous 24 hours
# lag_96 = previous 48 hours

lag_intervals = [1, 2, 3, 48, 96]

for lag in lag_intervals:
    df[f"demand_lag_{lag}"] = df["demand_w"].shift(lag)

# ------------------------------------------------------------
# Rolling historical features
# ------------------------------------------------------------

print("Creating rolling historical features...")

# IMPORTANT:
# shift(1) ensures the current target is NOT included
# in its own rolling feature.

past_demand = df["demand_w"].shift(1)

df["demand_rolling_mean_3"] = (
    past_demand
    .rolling(window=3)
    .mean()
)

df["demand_rolling_std_3"] = (
    past_demand
    .rolling(window=3)
    .std()
)

df["demand_rolling_mean_6"] = (
    past_demand
    .rolling(window=6)
    .mean()
)

df["demand_rolling_mean_48"] = (
    past_demand
    .rolling(window=48)
    .mean()
)

# ------------------------------------------------------------
# Historical maximum and minimum
# ------------------------------------------------------------

df["demand_rolling_max_48"] = (
    past_demand
    .rolling(window=48)
    .max()
)

df["demand_rolling_min_48"] = (
    past_demand
    .rolling(window=48)
    .min()
)

# ------------------------------------------------------------
# Remove rows with insufficient history
# ------------------------------------------------------------

before = len(df)

feature_columns = [
    "demand_lag_1",
    "demand_lag_2",
    "demand_lag_3",
    "demand_lag_48",
    "demand_lag_96",
    "demand_rolling_mean_3",
    "demand_rolling_std_3",
    "demand_rolling_mean_6",
    "demand_rolling_mean_48",
    "demand_rolling_max_48",
    "demand_rolling_min_48",
]

df = df.dropna(
    subset=feature_columns + ["demand_w"]
).reset_index(drop=True)

removed = before - len(df)

print(
    f"\nRows removed because of insufficient "
    f"historical information: {removed:,}"
)

print(f"Final feature rows: {len(df):,}")

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved feature dataset:")
print(OUTPUT_PATH)

# ------------------------------------------------------------
# Feature summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("FEATURE DATASET SUMMARY")
print("=" * 70)

print(f"Rows    : {len(df):,}")
print(f"Columns : {len(df.columns)}")

print("\nHistorical features:")

for column in feature_columns:
    print(f" - {column}")

print("\nCalendar features:")

calendar_features = [
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
]

for column in calendar_features:
    print(f" - {column}")

print("\nFirst 5 feature rows:")

print(
    df[
        [
            "timestamp",
            "demand_w",
            "demand_lag_1",
            "demand_lag_2",
            "demand_lag_48",
            "demand_lag_96",
            "demand_rolling_mean_48",
        ]
    ]
    .head()
    .to_string(index=False)
)

print("\nMissing values in engineered features:")

print(
    df[feature_columns]
    .isna()
    .sum()
    .to_string()
)

print("\nFeature engineering complete.")