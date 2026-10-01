from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
RAW_DIR = BASE_DIR / "datasets" / "solar" / "raw"

TRAIN_FILE = RAW_DIR / "train (1).csv"

df = pd.read_csv(TRAIN_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])

print("=" * 70)
print("DKA SOLAR OUTLIER ANALYSIS")
print("=" * 70)

numeric_cols = df.select_dtypes(include=np.number).columns

# ---------------------------------------------------------
# 1. Extreme values
# ---------------------------------------------------------
print("\nEXTREME VALUES")
print("-" * 70)

for col in numeric_cols:
    s = df[col]

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = ((s < lower) | (s > upper)).sum()

    print(f"\n{col}")
    print(f"  Q1              : {q1:.6f}")
    print(f"  Q3              : {q3:.6f}")
    print(f"  IQR             : {iqr:.6f}")
    print(f"  IQR lower bound : {lower:.6f}")
    print(f"  IQR upper bound : {upper:.6f}")
    print(f"  IQR outliers    : {outliers:,}")

# ---------------------------------------------------------
# 2. Show suspicious rows
# ---------------------------------------------------------
print("\n\nSUSPICIOUS SENSOR ROWS")
print("-" * 70)

checks = {
    "Wind_Speed": df["Wind_Speed"] < 0,
    "Wind_Direction": df["Wind_Direction"] < 0,
    "Global_Horizontal_Radiation": df["Global_Horizontal_Radiation"] < 0,
    "Active_Power": df["Active_Power"] < -0.1,
    "Radiation_Diffuse_Tilted": df["Radiation_Diffuse_Tilted"] > 5000,
}

for name, mask in checks.items():
    count = mask.sum()

    print(f"\n{name}: {count:,} suspicious rows")

    if count > 0:
        cols = ["timestamp", name]
        print(df.loc[mask, cols].head(10).to_string(index=False))

# ---------------------------------------------------------
# 3. Top extreme values
# ---------------------------------------------------------
print("\n\nTOP EXTREME VALUES")
print("-" * 70)

for col in numeric_cols:
    print(f"\n{col} - largest 5:")
    print(
        df[["timestamp", col]]
        .nlargest(5, col)
        .to_string(index=False)
    )

# ---------------------------------------------------------
# 4. Solar generation sanity check
# ---------------------------------------------------------
print("\n\nACTIVE POWER SANITY CHECK")
print("-" * 70)

print("Plant rated power: 23.4 kW")
print(f"Maximum observed Active_Power: {df['Active_Power'].max():.6f} kW")

above_capacity = (df["Active_Power"] > 23.4).sum()

print(f"Values above rated power: {above_capacity:,}")

# ---------------------------------------------------------
# 5. Negative active power
# ---------------------------------------------------------
print("\nNEGATIVE ACTIVE POWER")
print("-" * 70)

negative_power = df[df["Active_Power"] < 0]

print(f"Count: {len(negative_power):,}")

if len(negative_power) > 0:
    print("\nFirst 20:")
    print(
        negative_power[["timestamp", "Active_Power"]]
        .head(20)
        .to_string(index=False)
    )

# ---------------------------------------------------------
# 6. Night-time vs daytime
# ---------------------------------------------------------
print("\n\nDAY/NIGHT ACTIVE POWER")
print("-" * 70)

df["hour"] = df["timestamp"].dt.hour

night = df[(df["hour"] < 6) | (df["hour"] >= 20)]
day = df[(df["hour"] >= 6) & (df["hour"] < 20)]

print(f"Night rows: {len(night):,}")
print(f"Night mean power: {night['Active_Power'].mean():.6f} kW")
print(f"Night negative power: {(night['Active_Power'] < 0).sum():,}")

print(f"\nDay rows: {len(day):,}")
print(f"Day mean power: {day['Active_Power'].mean():.6f} kW")
print(f"Day negative power: {(day['Active_Power'] < 0).sum():,}")

print("\n" + "=" * 70)
print("OUTLIER ANALYSIS COMPLETE")
print("=" * 70)