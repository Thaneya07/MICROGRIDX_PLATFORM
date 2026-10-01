from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import loadmat


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"C:\MicroGridX_PLATFORM\microgridx")

RAW_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "battery_health"
    / "raw"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "datasets"
    / "battery_health"
    / "processed"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# BATTERY FILES
# ============================================================

BATTERY_FILES = [
    "B0005.mat",
    "B0006.mat",
    "B0007.mat",
    "B0018.mat",
]


# ============================================================
# MATLAB DATA HELPERS
# ============================================================

def unwrap_matlab(value):
    """
    Unwrap MATLAB object arrays until the actual underlying
    NumPy value is reached.

    MATLAB .mat files loaded with scipy.io.loadmat often contain
    nested object arrays. This helper removes those wrappers.
    """

    value = np.asarray(value)

    while value.dtype == object and value.size == 1:
        value = value.item()

    return value


def scalar_value(value):
    """
    Convert a MATLAB scalar/object field into a Python float.
    Returns NaN if conversion is not possible.
    """

    value = unwrap_matlab(value)

    arr = np.asarray(value).squeeze()

    if arr.size == 0:
        return np.nan

    try:
        return float(arr.flat[0])
    except (TypeError, ValueError):
        return np.nan


def numeric_array(value):
    """
    Convert a MATLAB measurement field into a 1D float array.

    Invalid/non-numeric values are ignored.
    """

    value = unwrap_matlab(value)

    arr = np.asarray(value).squeeze()

    if arr.size == 0:
        return np.array([], dtype=float)

    try:
        arr = arr.astype(float).reshape(-1)
    except (TypeError, ValueError):
        return np.array([], dtype=float)

    # Keep only finite values.
    arr = arr[np.isfinite(arr)]

    return arr


# ============================================================
# SAFE STATISTICS
# ============================================================

def safe_mean(arr):
    """Return mean or NaN if array is empty."""
    return float(np.mean(arr)) if arr.size else np.nan


def safe_std(arr):
    """Return standard deviation or NaN if array is empty."""
    return float(np.std(arr)) if arr.size else np.nan


def safe_min(arr):
    """Return minimum or NaN if array is empty."""
    return float(np.min(arr)) if arr.size else np.nan


def safe_max(arr):
    """Return maximum or NaN if array is empty."""
    return float(np.max(arr)) if arr.size else np.nan


# ============================================================
# EXTRACT ONE BATTERY
# ============================================================

def extract_battery(mat_path: Path) -> list[dict]:
    """
    Extract one row for every discharge cycle in a NASA
    battery .mat file.
    """

    print("\n" + "=" * 70)
    print(f"Processing {mat_path.name}")
    print("=" * 70)

    # --------------------------------------------------------
    # Load MATLAB file
    # --------------------------------------------------------

    mat = loadmat(mat_path)

    battery_id = mat_path.stem

    if battery_id not in mat:
        raise KeyError(
            f"Expected MATLAB variable '{battery_id}' "
            f"was not found in {mat_path.name}."
        )

    battery = mat[battery_id]

    # --------------------------------------------------------
    # Access cycle structure
    # --------------------------------------------------------

    cycle_struct = battery["cycle"][0, 0]

    total_cycles = cycle_struct.shape[1]

    print(f"Total experiment cycles: {total_cycles}")

    rows = []

    discharge_cycle_index = 0

    # --------------------------------------------------------
    # Process every cycle
    # --------------------------------------------------------

    for i in range(total_cycles):

        # ----------------------------------------------------
        # Cycle type
        # ----------------------------------------------------

        cycle_type_raw = cycle_struct["type"][0, i]

        cycle_type_value = unwrap_matlab(cycle_type_raw)

        if cycle_type_value.size == 0:
            continue

        try:
            cycle_type = str(cycle_type_value.flat[0]).strip().lower()
        except Exception:
            continue

        # ----------------------------------------------------
        # Only process discharge cycles
        # ----------------------------------------------------

        if cycle_type != "discharge":
            continue

        discharge_cycle_index += 1

        # MATLAB index starts at 1 conceptually
        cycle_number = i + 1

        # ----------------------------------------------------
        # Ambient temperature
        # ----------------------------------------------------

        ambient_temperature = scalar_value(
            cycle_struct["ambient_temperature"][0, i]
        )

        # ----------------------------------------------------
        # Data structure
        # ----------------------------------------------------

        data = cycle_struct["data"][0, i]

        field_names = data.dtype.names

        if field_names is None:
            print(
                f"WARNING: No data fields found for cycle "
                f"{cycle_number}"
            )
            continue

        # ----------------------------------------------------
        # Measurements
        # ----------------------------------------------------

        voltage = numeric_array(
            data["Voltage_measured"]
        )

        current = numeric_array(
            data["Current_measured"]
        )

        temperature = numeric_array(
            data["Temperature_measured"]
        )

        time = numeric_array(
            data["Time"]
        )

        # ----------------------------------------------------
        # Optional load measurements
        # ----------------------------------------------------

        if "Current_load" in field_names:
            current_load = numeric_array(
                data["Current_load"]
            )
        else:
            current_load = np.array([], dtype=float)

        if "Voltage_load" in field_names:
            voltage_load = numeric_array(
                data["Voltage_load"]
            )
        else:
            voltage_load = np.array([], dtype=float)

        # ----------------------------------------------------
        # Capacity
        # ----------------------------------------------------

        if "Capacity" in field_names:
            capacity_ah = scalar_value(
                data["Capacity"]
            )
        else:
            capacity_ah = np.nan

        # ----------------------------------------------------
        # Discharge duration
        # ----------------------------------------------------

        if time.size >= 2:

            duration_sec = float(
                time[-1] - time[0]
            )

        else:

            duration_sec = np.nan

        # ----------------------------------------------------
        # Create cycle-level feature row
        # ----------------------------------------------------

        row = {
            # Identification
            "battery_id": battery_id,
            "cycle": cycle_number,
            "discharge_cycle_index": discharge_cycle_index,

            # Operating conditions
            "ambient_temperature": ambient_temperature,

            # Target-related physical measurement
            "capacity_ah": capacity_ah,

            # Voltage features
            "voltage_mean": safe_mean(voltage),
            "voltage_min": safe_min(voltage),
            "voltage_max": safe_max(voltage),
            "voltage_std": safe_std(voltage),

            # Current features
            "current_mean": safe_mean(current),
            "current_min": safe_min(current),
            "current_max": safe_max(current),
            "current_std": safe_std(current),

            # Temperature features
            "temperature_mean": safe_mean(temperature),
            "temperature_min": safe_min(temperature),
            "temperature_max": safe_max(temperature),
            "temperature_std": safe_std(temperature),

            # Time
            "duration_sec": duration_sec,

            # Load measurements
            "current_load_mean": safe_mean(current_load),
            "voltage_load_mean": safe_mean(voltage_load),
        }

        rows.append(row)

    print(
        f"Discharge cycles extracted: "
        f"{len(rows)}"
    )

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "#" * 70)
    print("NASA BATTERY HEALTH FEATURE EXTRACTION")
    print("#" * 70)

    all_rows = []

    # --------------------------------------------------------
    # Process all battery files
    # --------------------------------------------------------

    for filename in BATTERY_FILES:

        mat_path = RAW_DIR / filename

        if not mat_path.exists():

            print(
                f"\nWARNING: File not found:\n"
                f"{mat_path}"
            )

            continue

        try:

            rows = extract_battery(mat_path)

            all_rows.extend(rows)

        except Exception as exc:

            print(
                f"\nERROR processing {filename}:"
            )

            print(exc)

    # --------------------------------------------------------
    # Check whether extraction succeeded
    # --------------------------------------------------------

    if not all_rows:

        raise RuntimeError(
            "No battery discharge data was extracted."
        )

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(all_rows)

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = (
        df
        .sort_values(
            [
                "battery_id",
                "discharge_cycle_index",
            ]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Save dataset
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        / "battery_discharge_features.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )

    # ========================================================
    # REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)

    print(
        f"Output file:\n{output_file}"
    )

    print(
        f"\nTotal rows: {len(df)}"
    )

    print(
        f"Total columns: {len(df.columns)}"
    )

    # --------------------------------------------------------
    # Rows per battery
    # --------------------------------------------------------

    print("\nRows by battery:")

    print(
        df.groupby("battery_id")
        .size()
        .to_string()
    )

    # --------------------------------------------------------
    # Capacity summary
    # --------------------------------------------------------

    print("\nCapacity summary:")

    capacity_summary = (
        df.groupby("battery_id")["capacity_ah"]
        .agg(
            [
                "count",
                "min",
                "max",
                "mean",
                "std",
            ]
        )
    )

    print(
        capacity_summary.to_string()
    )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------

    print("\nMissing values by column:")

    missing = df.isna().sum()

    print(
        missing.to_string()
    )

    # --------------------------------------------------------
    # First 10 rows
    # --------------------------------------------------------

    print("\nFirst 10 rows:")

    print(
        df.head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Last 10 rows
    # --------------------------------------------------------

    print("\nLast 10 rows:")

    print(
        df.tail(10)
        .to_string(index=False)
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()