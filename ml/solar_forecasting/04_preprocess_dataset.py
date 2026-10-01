from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
RAW_DIR = BASE_DIR / "datasets" / "solar" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "solar" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = RAW_DIR / "train (1).csv"
TEST_FILE = RAW_DIR / "test (1).csv"

OUTPUT_TRAIN = PROCESSED_DIR / "solar_train_clean.csv"
OUTPUT_TEST = PROCESSED_DIR / "solar_test_clean.csv"

print("=" * 70)
print("DKA SOLAR DATASET PREPROCESSING")
print("=" * 70)

train = pd.read_csv(TRAIN_FILE)
test = pd.read_csv(TEST_FILE)

# ---------------------------------------------------------
# 1. Parse timestamps
# ---------------------------------------------------------

train["timestamp"] = pd.to_datetime(train["timestamp"])
test["timestamp"] = pd.to_datetime(test["timestamp"])

train = train.sort_values("timestamp").reset_index(drop=True)
test = test.sort_values("timestamp").reset_index(drop=True)

# ---------------------------------------------------------
# 2. Remove duplicate timestamps
# ---------------------------------------------------------

train = train.drop_duplicates(subset="timestamp", keep="first")
test = test.drop_duplicates(subset="timestamp", keep="first")

# ---------------------------------------------------------
# 3. Handle clearly invalid sensor values
# ---------------------------------------------------------

# Wind speed cannot physically be negative.
train.loc[train["Wind_Speed"] < 0, "Wind_Speed"] = np.nan
test.loc[test["Wind_Speed"] < 0, "Wind_Speed"] = np.nan

# Wind direction should be within 0–360 degrees.
train.loc[
    (train["Wind_Direction"] < 0) |
    (train["Wind_Direction"] > 360),
    "Wind_Direction"
] = np.nan

test.loc[
    (test["Wind_Direction"] < 0) |
    (test["Wind_Direction"] > 360),
    "Wind_Direction"
] = np.nan

# Relative humidity is bounded approximately between 0 and 100%.
train.loc[
    (train["Weather_Relative_Humidity"] < 0) |
    (train["Weather_Relative_Humidity"] > 100),
    "Weather_Relative_Humidity"
] = np.nan

test.loc[
    (test["Weather_Relative_Humidity"] < 0) |
    (test["Weather_Relative_Humidity"] > 100),
    "Weather_Relative_Humidity"
] = np.nan

# Radiation cannot physically be negative.
radiation_columns = [
    "Global_Horizontal_Radiation",
    "Diffuse_Horizontal_Radiation",
    "Radiation_Global_Tilted",
    "Radiation_Diffuse_Tilted",
]

for col in radiation_columns:
    train.loc[train[col] < 0, col] = np.nan
    test.loc[test[col] < 0, col] = np.nan

# ---------------------------------------------------------
# 4. Handle clearly corrupted diffuse tilted radiation
# ---------------------------------------------------------

# The observed 45,955–97,323 values are far outside
# the normal range of the dataset and are treated as
# corrupted sensor readings.

train.loc[
    train["Radiation_Diffuse_Tilted"] > 5000,
    "Radiation_Diffuse_Tilted"
] = np.nan

test.loc[
    test["Radiation_Diffuse_Tilted"] > 5000,
    "Radiation_Diffuse_Tilted"
] = np.nan

# ---------------------------------------------------------
# 5. Handle tiny negative PV output
# ---------------------------------------------------------

# Small negative values occur around zero-generation periods.
# They are treated as zero because PV generation cannot be
# negative for the forecasting target.

train.loc[train["Active_Power"] < 0, "Active_Power"] = 0.0

# ---------------------------------------------------------
# 6. Impute missing feature values
# ---------------------------------------------------------

feature_columns = [
    "Wind_Speed",
    "Weather_Temperature_Celsius",
    "Weather_Relative_Humidity",
    "Global_Horizontal_Radiation",
    "Diffuse_Horizontal_Radiation",
    "Wind_Direction",
    "Weather_Daily_Rainfall",
    "Radiation_Global_Tilted",
    "Radiation_Diffuse_Tilted",
]

# Time interpolation followed by forward/backward fill.
# This is applied only to input features, never to the target.

for col in feature_columns:
    train[col] = (
        train[col]
        .interpolate(method="linear", limit_direction="both")
    )

    test[col] = (
        test[col]
        .interpolate(method="linear", limit_direction="both")
    )

# ---------------------------------------------------------
# 7. Add basic calendar features
# ---------------------------------------------------------

for df in [train, test]:

    df["hour"] = df["timestamp"].dt.hour
    df["minute"] = df["timestamp"].dt.minute

    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["day_of_year"] = df["timestamp"].dt.dayofyear
    df["month"] = df["timestamp"].dt.month

    # Cyclic time features
    df["hour_sin"] = np.sin(
        2 * np.pi *
        (df["hour"] * 60 + df["minute"]) / (24 * 60)
    )

    df["hour_cos"] = np.cos(
        2 * np.pi *
        (df["hour"] * 60 + df["minute"]) / (24 * 60)
    )

    df["day_of_year_sin"] = np.sin(
        2 * np.pi * df["day_of_year"] / 365.25
    )

    df["day_of_year_cos"] = np.cos(
        2 * np.pi * df["day_of_year"] / 365.25
    )

# ---------------------------------------------------------
# 8. Verify final data
# ---------------------------------------------------------

print("\nFINAL DATASET")
print("-" * 70)

print("Train rows:", len(train))
print("Test rows :", len(test))

print("\nTrain missing values:")
print(train.isna().sum()[train.isna().sum() > 0])

print("\nTest missing values:")
print(test.isna().sum()[test.isna().sum() > 0])

print("\nTrain Active_Power:")
print(f"Min : {train['Active_Power'].min():.6f} kW")
print(f"Max : {train['Active_Power'].max():.6f} kW")
print(f"Mean: {train['Active_Power'].mean():.6f} kW")

# ---------------------------------------------------------
# 9. Save
# ---------------------------------------------------------

train.to_csv(OUTPUT_TRAIN, index=False)
test.to_csv(OUTPUT_TEST, index=False)

print("\nSaved:")
print(OUTPUT_TRAIN)
print(OUTPUT_TEST)

print("\n" + "=" * 70)
print("PREPROCESSING COMPLETE")
print("=" * 70)