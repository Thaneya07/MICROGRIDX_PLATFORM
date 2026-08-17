import type { DeviceSnapshotReading, DeviceType, MicrogridSnapshot } from "@/types/telemetry";

export function devicesByType(snapshot: MicrogridSnapshot, type: DeviceType): DeviceSnapshotReading[] {
  return snapshot.devices.filter((d) => d.device_type === type);
}

export function isDeviceOnline(device: DeviceSnapshotReading | undefined): boolean {
  return device?.status === "ONLINE";
}

export type BatteryFlowState = "charging" | "discharging" | "idle" | "unknown";

/** Battery charge/discharge state derived from the signed microgrid-level battery_power_w. */
export function getBatteryFlowState(snapshot: MicrogridSnapshot): BatteryFlowState {
  const power = snapshot.energy_reading?.battery_power_w;
  if (power === null || power === undefined) return "unknown";
  if (power > 1) return "discharging";
  if (power < -1) return "charging";
  return "idle";
}

export type GridFlowState = "importing" | "exporting" | "balanced" | "unknown";

/** Grid import/export direction derived from the microgrid-level energy reading. */
export function getGridFlowState(snapshot: MicrogridSnapshot): GridFlowState {
  const reading = snapshot.energy_reading;
  if (!reading) return "unknown";
  if (reading.grid_import_w > reading.grid_export_w && reading.grid_import_w > 1) return "importing";
  if (reading.grid_export_w > reading.grid_import_w && reading.grid_export_w > 1) return "exporting";
  return "balanced";
}

export function hasLiveData(snapshot: MicrogridSnapshot | null): boolean {
  return snapshot !== null && snapshot.energy_reading !== null;
}

export function isSimulated(snapshot: MicrogridSnapshot | null): boolean {
  return snapshot?.source === "SIMULATED";
}

export function isHardware(snapshot: MicrogridSnapshot | null): boolean {
  return snapshot?.source === "HARDWARE";
}

export function getGenerationW(snapshot: MicrogridSnapshot): number {
  return snapshot.energy_reading?.generation_w ?? 0;
}

export function getConsumptionW(snapshot: MicrogridSnapshot): number {
  return snapshot.energy_reading?.consumption_w ?? 0;
}
