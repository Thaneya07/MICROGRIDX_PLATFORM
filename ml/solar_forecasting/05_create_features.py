from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
INPUT = BASE_DIR / "datasets" / "solar" / "processed" / "solar_train_clean.csv"
OUTPUT = BASE_DIR / "datasets" / "solar" / "processed" / "solar_features.csv"

df = pd.read_csv(INPUT, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

print("=" * 70)
print("SOLAR FEATURE ENGINEERING")
print("=" * 70)

# Previous PV-power observations
for lag in [1, 2, 3, 6, 12, 24, 288, 576]:
    df[f"power_lag_{lag}"] = df["Active_Power"].shift(lag)

# Rolling statistics — shift first to prevent target leakage
shifted = df["Active_Power"].shift(1)

for window in [3, 6, 12, 24, 288]:
    df[f"power_roll_mean_{window}"] = shifted.rolling(window).mean()

for window in [6, 24, 288]:
    df[f"power_roll_std_{window}"] = shifted.rolling(window).std()

# Solar-radiation interactions
df["radiation_ratio"] = (
    df["Radiation_Global_Tilted"] /
    (df["Global_Horizontal_Radiation"] + 1e-6)
)

df["diffuse_ratio"] = (
    df["Diffuse_Horizontal_Radiation"] /
    (df["Global_Horizontal_Radiation"] + 1e-6)
)

# Cyclic features
df["solar_time_sin"] = np.sin(
    2 * np.pi *
    (df["hour"] * 60 + df["minute"]) / (24 * 60)
)

df["solar_time_cos"] = np.cos(
    2 * np.pi *
    (df["hour"] * 60 + df["minute"]) / (24 * 60)
)

# Remove rows without enough historical information
before = len(df)
df = df.dropna().reset_index(drop=True)
removed = before - len(df)

print(f"Input rows        : {before:,}")
print(f"Rows removed      : {removed:,}")
print(f"Final rows        : {len(df):,}")
print(f"Final columns     : {len(df.columns)}")
print(f"Missing values    : {df.isna().sum().sum():,}")

df.to_csv(OUTPUT, index=False)

print("\nSaved:")
print(OUTPUT)

print("\n" + "=" * 70)
print("FEATURE ENGINEERING COMPLETE")
print("=" * 70)