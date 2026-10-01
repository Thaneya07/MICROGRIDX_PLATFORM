from pathlib import Path
import pandas as pd

# ============================================================
# MicroGridX - Demand Forecasting
# Step 1: Raw Dataset Inspection
# ============================================================

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "datasets"
    / "demand"
    / "raw"
    / "household_power_consumption.txt"
)

print("=" * 70)
print("MicroGridX Demand Forecasting - Dataset Inspection")
print("=" * 70)

print(f"\nDataset path:\n{DATA_PATH}")
print(f"File exists: {DATA_PATH.exists()}")

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

print("\nLoading dataset...")

df = pd.read_csv(
    DATA_PATH,
    sep=";",
    na_values="?",
    low_memory=False,
)

print("\nDataset loaded successfully.")

# ------------------------------------------------------------
# Basic information
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("1. DATASET SHAPE")
print("=" * 70)

print(f"Rows    : {len(df):,}")
print(f"Columns : {len(df.columns)}")

# ------------------------------------------------------------
# Columns
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("2. COLUMNS")
print("=" * 70)

for i, column in enumerate(df.columns, start=1):
    print(f"{i:2}. {column}")

# ------------------------------------------------------------
# First and last records
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("3. FIRST 5 ROWS")
print("=" * 70)

print(df.head().to_string())

print("\n" + "=" * 70)
print("4. LAST 5 ROWS")
print("=" * 70)

print(df.tail().to_string())

# ------------------------------------------------------------
# Missing values
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("5. MISSING VALUES")
print("=" * 70)

missing = df.isna().sum()

missing_table = pd.DataFrame(
    {
        "missing_count": missing,
        "missing_percentage": (missing / len(df) * 100).round(4),
    }
)

print(missing_table.to_string())

print(
    f"\nTotal missing cells: {int(df.isna().sum().sum()):,}"
)

# ------------------------------------------------------------
# Convert date/time
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("6. DATE RANGE")
print("=" * 70)

df["timestamp"] = pd.to_datetime(
    df["Date"] + " " + df["Time"],
    dayfirst=True,
    errors="coerce",
)

print(f"Start: {df['timestamp'].min()}")
print(f"End  : {df['timestamp'].max()}")

invalid_timestamps = df["timestamp"].isna().sum()

print(f"Invalid timestamps: {invalid_timestamps:,}")

# ------------------------------------------------------------
# Duplicate timestamps
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("7. DUPLICATE TIMESTAMPS")
print("=" * 70)

duplicate_count = df["timestamp"].duplicated().sum()

print(f"Duplicate timestamps: {duplicate_count:,}")

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
    df[column] = pd.to_numeric(df[column], errors="coerce")

# ------------------------------------------------------------
# Demand statistics
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("8. GLOBAL ACTIVE POWER STATISTICS")
print("=" * 70)

demand = df["Global_active_power"]

print(f"Valid observations : {demand.notna().sum():,}")
print(f"Missing observations: {demand.isna().sum():,}")
print(f"Minimum (kW)       : {demand.min()}")
print(f"Maximum (kW)       : {demand.max()}")
print(f"Mean (kW)          : {demand.mean():.4f}")
print(f"Median (kW)        : {demand.median():.4f}")
print(f"Std. deviation     : {demand.std():.4f}")

# ------------------------------------------------------------
# Data types
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("9. DATA TYPES")
print("=" * 70)

print(df.dtypes.to_string())

# ------------------------------------------------------------
# Final summary
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)

print("\nNo preprocessing or data modification was performed.")
print("The original UCI dataset remains unchanged.")