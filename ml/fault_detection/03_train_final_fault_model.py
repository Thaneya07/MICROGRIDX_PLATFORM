from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder


PROJECT_ROOT = Path(
    r"C:\MicroGridX_PLATFORM\microgridx"
)

INPUT_FILE = (
    PROJECT_ROOT
    / "datasets"
    / "fault_detection"
    / "raw"
    / "Fault_dataset.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "ml"
    / "fault_detection"
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


FEATURES = [
    "EA",
    "EB",
    "EC",
]

TARGET = "Class"


df = pd.read_csv(INPUT_FILE)

X = df[FEATURES].copy()

y_text = df[TARGET].astype(str)

encoder = LabelEncoder()

y = encoder.fit_transform(y_text)


model = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    min_samples_leaf=1,
    random_state=42,
    n_jobs=-1,
)

model.fit(
    X,
    y
)


model_path = (
    MODEL_DIR
    / "fault_random_forest.joblib"
)

encoder_path = (
    MODEL_DIR
    / "fault_label_encoder.joblib"
)

joblib.dump(
    model,
    model_path
)

joblib.dump(
    encoder,
    encoder_path
)


print("=" * 70)
print("FINAL FAULT DETECTION MODEL")
print("=" * 70)

print(f"Training samples: {len(df)}")
print(f"Features: {FEATURES}")
print(f"Classes: {encoder.classes_.tolist()}")

print("\nModel saved:")
print(model_path)

print("\nEncoder saved:")
print(encoder_path)

print("=" * 70)
print("FINAL MODEL TRAINING COMPLETE")
print("=" * 70)