import json

from pathlib import Path
import sys


PROJECT_ROOT = Path(
    r"C:\MicroGridX_PLATFORM\microgridx"
)

sys.path.insert(
    0,
    str(
        PROJECT_ROOT
        / "backend"
    )
)

from app.services.battery_health.service import (
    predict_battery_health,
)


sample_features = {
    "ambient_temperature": 24.0,

    "voltage_mean": 3.53,
    "voltage_min": 2.61,
    "voltage_max": 4.19,
    "voltage_std": 0.236,

    "current_mean": -1.82,
    "current_min": -2.02,
    "current_max": 0.001,
    "current_std": 0.59,

    "temperature_mean": 32.57,
    "temperature_min": 24.33,
    "temperature_max": 38.98,
    "temperature_std": 3.49,

    "duration_sec": 3690.234,

    "current_load_mean": -1.81,
    "voltage_load_mean": 2.40,

    "discharge_cycle_index": 1,
}


result = predict_battery_health(
    sample_features
)

print(
    json.dumps(
        result,
        indent=2
    )
)