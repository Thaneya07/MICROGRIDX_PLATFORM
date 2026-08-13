from app.models import Base, EnergyReading, DeviceReading, TelemetrySource


def test_telemetry_models_import_successfully():
    assert EnergyReading.__tablename__ == "energy_readings"
    assert DeviceReading.__tablename__ == "device_readings"


def test_telemetry_tables_registered_in_metadata():
    table_names = set(Base.metadata.tables.keys())
    assert {"energy_readings", "device_readings"}.issubset(table_names)


def test_telemetry_source_enum_values():
    assert {s.value for s in TelemetrySource} == {"SIMULATED", "HARDWARE"}


def test_energy_reading_has_expected_columns():
    columns = {c.name for c in EnergyReading.__table__.columns}
    assert {
        "id",
        "microgrid_id",
        "recorded_at",
        "consumption_w",
        "generation_w",
        "grid_import_w",
        "grid_export_w",
        "available_energy_w",
        "battery_soc_percent",
        "source",
        "created_at",
    }.issubset(columns)


def test_device_reading_has_expected_columns():
    columns = {c.name for c in DeviceReading.__table__.columns}
    assert {
        "id",
        "device_id",
        "recorded_at",
        "power_w",
        "voltage_v",
        "current_a",
        "status",
        "source",
        "created_at",
    }.issubset(columns)
