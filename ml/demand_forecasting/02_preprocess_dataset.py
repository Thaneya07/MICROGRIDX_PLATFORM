from pathlib import Path
import pandas as pd

# ============================================================
# MicroGridX - Demand Forecasting
# Step 2: Dataset Preprocessing
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_PATH = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "raw"
    / "household_power_consumption.txt"
)

OUTPUT_DIR = (
    BASE_DIR
    / "datasets"
    / "demand"
    / "processed"
)

OUTPUT_PATH = OUTPUT_DIR / "demand_30min.csv"

print("=" * 70)
print("MicroGridX Demand Forecasting - Preprocessing")
print("=" * 70)

# ------------------------------------------------------------
# Create output directory
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Load raw dataset
# ------------------------------------------------------------

print("\nLoading raw dataset...")

df = pd.read_csv(
    RAW_PATH,
    sep=";",
    na_values="?",
    low_memory=False,
)

print(f"Raw rows: {len(df):,}")

# ------------------------------------------------------------
# Create timestamp
# ------------------------------------------------------------

df["timestamp"] = pd.to_datetime(
    df["Date"] + " " + df["Time"],
    dayfirst=True,
    errors="coerce",
)

# ------------------------------------------------------------
# Convert numerical columns
# ------------------------------------------------------------

numeric_columns = [
    "Global_active_power",
    "Global_reactive_power",
    "Voltage",
    "Global_intensity",
    "Sub_metering_1",
    "Sub_metering_2",
    "Sub_metering_3",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )

# ------------------------------------------------------------
# Keep required columns
# ------------------------------------------------------------

df = df[
    [
        "timestamp",
        "Global_active_power",
        "Global_reactive_power",
        "Voltage",
        "Global_intensity",
        "Sub_metering_1",
        "Sub_metering_2",
        "Sub_metering_3",
    ]
]

# ------------------------------------------------------------
# Sort chronologically
# ------------------------------------------------------------

df = df.sort_values("timestamp")

# ------------------------------------------------------------
# Resample to 30-minute intervals
# ------------------------------------------------------------

print("\nAggregating to 30-minute intervals...")

df = df.set_index("timestamp")

aggregated = df.resample("30min").agg(
    {
        "Global_active_power": "mean",
        "Global_reactive_power": "mean",
        "Voltage": "mean",
        "Global_intensity": "mean",
        "Sub_metering_1": "mean",
        "Sub_metering_2": "mean",
        "Sub_metering_3": "mean",
    }
)

# ------------------------------------------------------------
# Rename columns
# ------------------------------------------------------------

aggregated = aggregated.rename(
    columns={
        "Global_active_power": "demand_kw",
        "Global_reactive_power": "reactive_power_kw",
        "Voltage": "voltage_v",
        "Global_intensity": "current_a",
        "Sub_metering_1": "sub_metering_1_wh",
        "Sub_metering_2": "sub_metering_2_wh",
        "Sub_metering_3": "sub_metering_3_wh",
    }
)

# ------------------------------------------------------------
# Convert demand from kW to W
# ------------------------------------------------------------

aggregated["demand_w"] = (
    aggregated["demand_kw"] * 1000
)

# ------------------------------------------------------------
# Calendar features
# ------------------------------------------------------------

aggregated["hour"] = aggregated.index.hour

aggregated["minute"] = aggregated.index.minute

aggregated["day_of_week"] = (
    aggregated.index.dayofweek
)

aggregated["day_of_month"] = (
    aggregated.index.day
)

aggregated["month"] = (
    aggregated.index.month
)

aggregated["is_weekend"] = (
    aggregated["day_of_week"] >= 5
).astype(int)

# ------------------------------------------------------------
# Reset index
# ------------------------------------------------------------

aggregated = aggregated.reset_index()

# ------------------------------------------------------------
# Remove intervals with missing target
# ------------------------------------------------------------

before = len(aggregated)

aggregated = aggregated.dropna(
    subset=["demand_w"]
)

removed = before - len(aggregated)

print(f"\n30-minute intervals before target filtering: {before:,}")
print(f"Intervals removed due to missing demand: {removed:,}")
print(f"Final intervals: {len(aggregated):,}")

# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

aggregated.to_csv(
    OUTPUT_PATH,
    index=False,
)

print("\nSaved processed dataset:")
print(OUTPUT_PATH)

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("PROCESSED DATASET SUMMARY")
print("=" * 70)

print(f"Rows       : {len(aggregated):,}")
print(f"Columns    : {len(aggregated.columns)}")
print(f"Start      : {aggregated['timestamp'].min()}")
print(f"End        : {aggregated['timestamp'].max()}")

print(
    f"Demand mean: "
    f"{aggregated['demand_w'].mean():.2f} W"
)

print(
    f"Demand min : "
    f"{aggregated['demand_w'].min():.2f} W"
)

print(
    f"Demand max : "
    f"{aggregated['demand_w'].max():.2f} W"
)

print("\nColumns:")

for column in aggregated.columns:
    print(f" - {column}")

print("\nFirst 5 rows:")
print(aggregated.head().to_string(index=False))

print("\nPreprocessing complete.")