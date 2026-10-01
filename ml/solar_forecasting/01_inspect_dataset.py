from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"C:\MicroGridX_PLATFORM\microgridx")
RAW_DIR = BASE_DIR / "datasets" / "solar" / "raw"

TRAIN_FILE = RAW_DIR / "train (1).csv"
TEST_FILE = RAW_DIR / "test (1).csv"


def inspect_file(path):
    print("\n" + "=" * 70)
    print(f"FILE: {path.name}")
    print("=" * 70)

    df = pd.read_csv(path)

    print(f"\nRows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\nColumns:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i:2}. {col}")

    print("\nData types:")
    print(df.dtypes)

    print("\nFirst 5 rows:")
    print(df.head().to_string())

    print("\nMissing values:")
    missing = df.isna().sum()
    print(missing[missing > 0])

    print("\nDuplicate rows:", df.duplicated().sum())

    print("\nBasic statistics:")
    print(df.describe(include="all").transpose().to_string())

    return df


print("DKA SOLAR DATASET INSPECTION")
print("=" * 70)

train = inspect_file(TRAIN_FILE)
test = inspect_file(TEST_FILE)

print("\n" + "=" * 70)
print("TRAIN vs TEST")
print("=" * 70)

print(f"Train shape: {train.shape}")
print(f"Test shape : {test.shape}")

print("\nInspection complete.")