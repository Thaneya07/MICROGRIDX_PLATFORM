from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
INPUT = BASE_DIR / "datasets" / "solar" / "processed" / "solar_features.csv"
OUT = BASE_DIR / "datasets" / "solar" / "processed"

df = pd.read_csv(INPUT, parse_dates=["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)

n = len(df)

train_end = int(n * 0.70)
val_end = int(n * 0.85)

train = df.iloc[:train_end].copy()
validation = df.iloc[train_end:val_end].copy()
test = df.iloc[val_end:].copy()

train.to_csv(OUT / "solar_train.csv", index=False)
validation.to_csv(OUT / "solar_validation.csv", index=False)
test.to_csv(OUT / "solar_test.csv", index=False)

print("=" * 70)
print("SOLAR CHRONOLOGICAL SPLIT")
print("=" * 70)

print(f"Total      : {n:,}")
print(f"Train      : {len(train):,}")
print(f"Validation : {len(validation):,}")
print(f"Test       : {len(test):,}")

print("\nTime ranges:")
print(f"Train      : {train['timestamp'].min()} -> {train['timestamp'].max()}")
print(f"Validation : {validation['timestamp'].min()} -> {validation['timestamp'].max()}")
print(f"Test       : {test['timestamp'].min()} -> {test['timestamp'].max()}")

print("\nChronological check:")

assert train["timestamp"].max() < validation["timestamp"].min()
assert validation["timestamp"].max() < test["timestamp"].min()

print("PASS")

print("\nSaved:")
print(OUT / "solar_train.csv")
print(OUT / "solar_validation.csv")
print(OUT / "solar_test.csv")