import type { DeviceSnapshotReading, LoadSnapshot, MicrogridSnapshot } from "@/types/telemetry";
import type { SelectedComponent } from "./selection";

export function buildSolarDetails(snapshot: MicrogridSnapshot, device?: DeviceSnapshotReading): SelectedComponent {
  const reading = snapshot.energy_reading;
  return {
    kind: "solar",
    title: "Solar Array",
    details: [
      { label: "Status", value: device?.status ?? "UNKNOWN" },
      { label: "Generation", value: reading ? `${reading.generation_w.toFixed(0)} W` : "—" },
      { label: "Device voltage", value: device ? `${device.voltage_v.toFixed(1)} V` : "—" },
      { label: "Device current", value: device ? `${device.current_a.toFixed(2)} A` : "—" },
    ],
  };
}

export function buildBatteryDetails(snapshot: MicrogridSnapshot, device?: DeviceSnapshotReading): SelectedComponent {
  const reading = snapshot.energy_reading;
  const powerW = reading?.battery_power_w ?? null;
  const flowLabel = powerW === null ? "Unknown" : powerW > 1 ? "Discharging" : powerW < -1 ? "Charging" : "Idle";
  return {
    kind: "battery",
    title: "Battery Storage",
    details: [
      { label: "Status", value: device?.status ?? "UNKNOWN" },
      { label: "State of charge", value: reading?.battery_soc_percent !== null && reading?.battery_soc_percent !== undefined ? `${reading.battery_soc_percent.toFixed(0)} %` : "—" },
      { label: "Power flow", value: flowLabel },
      { label: "Power", value: powerW !== null ? `${Math.abs(powerW).toFixed(0)} W` : "—" },
    ],
  };
}

export function buildGridDetails(snapshot: MicrogridSnapshot, device?: DeviceSnapshotReading): SelectedComponent {
  const reading = snapshot.energy_reading;
  const importW = reading?.grid_import_w ?? 0;
  const exportW = reading?.grid_export_w ?? 0;
  const direction = importW > exportW && importW > 1 ? "Importing" : exportW > importW && exportW > 1 ? "Exporting" : "Balanced";
  return {
    kind: "grid",
    title: "Grid Connection / Meter",
    details: [
      { label: "Status", value: device?.status ?? "UNKNOWN" },
      { label: "Direction", value: direction },
      { label: "Import", value: `${importW.toFixed(0)} W` },
      { label: "Export", value: `${exportW.toFixed(0)} W` },
    ],
  };
}

export function buildLoadControllerDetails(loads: LoadSnapshot[], device?: DeviceSnapshotReading): SelectedComponent {
  const onCount = loads.filter((l) => l.status === "ON").length;
  return {
    kind: "loadController",
    title: "Load Controller",
    details: [
      { label: "Status", value: device?.status ?? "UNKNOWN" },
      { label: "Managed loads", value: String(loads.length) },
      { label: "Active loads", value: String(onCount) },
    ],
  };
}

export function buildLoadDetails(load: LoadSnapshot): SelectedComponent {
  return {
    kind: "load",
    title: load.name,
    details: [
      { label: "Status", value: load.status },
      { label: "Category", value: load.category },
      { label: "Priority", value: String(load.priority) },
      { label: "Controllable", value: load.controllable ? "Yes" : "No" },
      { label: "Control mode", value: load.control_mode },
    ],
  };
}

export function buildSensorDetails(device: DeviceSnapshotReading): SelectedComponent {
  return {
    kind: "sensor",
    title: "Sensor",
    details: [
      { label: "Status", value: device.status },
      { label: "Voltage", value: `${device.voltage_v.toFixed(1)} V` },
      { label: "Current", value: `${device.current_a.toFixed(2)} A` },
      { label: "Source", value: device.source },
    ],
  };
}
