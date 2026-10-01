import json
import re
import time
import urllib.request

import serial


# =========================
# MicroGridX Hardware Bridge
# =========================

SERIAL_PORT = "COM11"
BAUD_RATE = 115200

BACKEND_URL = "http://localhost:8000/api/telemetry/hardware"

DEVICE_ID = "esp32-01"


def send_telemetry(temperature, humidity):
    payload = {
        "device_id": DEVICE_ID,

        "temperature_c": temperature,
        "humidity_percent": humidity,

        # INA219 is not yet connected to the actual
        # solar/battery power circuit.
        "solar_voltage_v": None,
        "solar_current_a": None,
        "solar_power_w": None,

        "battery_voltage_v": None,
        "battery_current_a": None,
        "battery_power_w": None,

        "relay_state": False,
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        BACKEND_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            result = response.read().decode("utf-8")

        print("Backend response:")
        print(result)
        print("-" * 50)

    except Exception as error:
        print("ERROR sending telemetry:")
        print(error)
        print("-" * 50)


def main():
    print("=" * 50)
    print("MicroGridX ESP32 Hardware Bridge")
    print("=" * 50)

    print(f"Opening ESP32 serial port: {SERIAL_PORT}")

    try:
        ser = serial.Serial(
            SERIAL_PORT,
            BAUD_RATE,
            timeout=1,
        )
    except Exception as error:
        print("Could not open ESP32 serial port.")
        print(error)
        return

    print("ESP32 connected.")
    print("Waiting for telemetry...")
    print("=" * 50)

    temperature = None
    humidity = None

    while True:
        try:
            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not line:
                continue

            print(f"ESP32: {line}")

            # Example:
            # Temperature: 37.50 °C
            temp_match = re.search(
                r"Temperature:\s*(-?\d+(?:\.\d+)?)",
                line
            )

            if temp_match:
                temperature = float(temp_match.group(1))

            # Example:
            # Humidity: 65.80 %
            humidity_match = re.search(
                r"Humidity:\s*(-?\d+(?:\.\d+)?)",
                line
            )

            if humidity_match:
                humidity = float(humidity_match.group(1))

            # When both readings are available,
            # send them to FastAPI.
            if temperature is not None and humidity is not None:
                print()
                print("Sending telemetry to MicroGridX backend...")

                send_telemetry(
                    temperature,
                    humidity
                )

                temperature = None
                humidity = None

        except KeyboardInterrupt:
            print()
            print("Bridge stopped.")
            break

        except Exception as error:
            print("Serial reading error:")
            print(error)
            time.sleep(1)

    ser.close()


if __name__ == "__main__":
    main()