from pathlib import Path
import pandas as pd
import numpy as np

# ============================================================
# MicroGridX - Demand Forecasting
# Step 7: Enhanced Time-Series Feature Engineering
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
    / "demand_enhanced_features.csv"
)

print("=" * 70)
print("MicroGridX Demand Forecasting - Enhanced Features")
print("=" * 70)

# ------------------------------------------------------------
# Load processed data
# ------------------------------------------------------------

df = pd.read_csv(INPUT_PATH)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = (
    df.sort_values("timestamp")
    .reset_index(drop=True)
)

print(f"\nInput rows: {len(df):,}")

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
# Past demand series
# ------------------------------------------------------------

past_demand = df["demand_w"].shift(1)

# ------------------------------------------------------------
# Lag features
# ------------------------------------------------------------

print("Creating lag features...")

lag_intervals = [
    1,      # 30 minutes
    2,      # 1 hour
    3,      # 1.5 hours
    48,     # 24 hours
    96,     # 48 hours
    336,    # 7 days
]

for lag in lag_intervals:
    df[f"demand_lag_{lag}"] = (
        df["demand_w"].shift(lag)
    )

# ------------------------------------------------------------
# Short-term rolling features
# ------------------------------------------------------------

print("Creating short-term rolling features...")

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

df["demand_rolling_std_6"] = (
    past_demand
    .rolling(window=6)
    .std()
)

# ------------------------------------------------------------
# Daily rolling features
# ------------------------------------------------------------

print("Creating daily rolling features...")

df["demand_rolling_mean_48"] = (
    past_demand
    .rolling(window=48)
    .mean()
)

df["demand_rolling_std_48"] = (
    past_demand
    .rolling(window=48)
    .std()
)

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
# Weekly rolling features
# ------------------------------------------------------------

print("Creating weekly rolling features...")

df["demand_rolling_mean_336"] = (
    past_demand
    .rolling(window=336)
    .mean()
)

df["demand_rolling_std_336"] = (
    past_demand
    .rolling(window=336)
    .std()
)

# ------------------------------------------------------------
# Remove rows without sufficient history
# ------------------------------------------------------------

feature_columns = [
    "demand_lag_1",
    "demand_lag_2",
    "demand_lag_3",
    "demand_lag_48",
    "demand_lag_96",
    "demand_lag_336",

    "demand_rolling_mean_3",
    "demand_rolling_std_3",

    "demand_rolling_mean_6",
    "demand_rolling_std_6",

    "demand_rolling_mean_48",
    "demand_rolling_std_48",
    "demand_rolling_max_48",
    "demand_rolling_min_48",

    "demand_rolling_mean_336",
    "demand_rolling_std_336",
]

before = len(df)

df = (
    df.dropna(
        subset=feature_columns + ["demand_w"]
    )
    .reset_index(drop=True)
)

removed = before - len(df)

print(
    f"\nRows removed because of insufficient history: "
    f"{removed:,}"
)

print(f"Final rows: {len(df):,}")

# ------------------------------------------------------------
# Verify feature completeness
# ------------------------------------------------------------

missing_features = (
    df[feature_columns]
    .isna()
    .sum()
    .sum()
)

print(
    f"Missing values in engineered features: "
    f"{missing_features}"
)

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\nSaved enhanced feature dataset:")
print(OUTPUT_PATH)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("ENHANCED FEATURE SUMMARY")
print("=" * 70)

print(f"Rows    : {len(df):,}")
print(f"Columns : {len(df.columns)}")

print("\nNew historical features include:")

for column in feature_columns:
    print(f" - {column}")

print("\nFirst 5 rows:")

print(
    df[
        [
            "timestamp",
            "demand_w",
            "demand_lag_1",
            "demand_lag_48",
            "demand_lag_96",
            "demand_lag_336",
            "demand_rolling_mean_336",
        ]
    ]
    .head()
    .to_string(index=False)
)

print("\nEnhanced feature engineering complete.")