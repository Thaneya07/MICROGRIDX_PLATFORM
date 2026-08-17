/**
 * Types mirroring app/schemas/telemetry_snapshot.py exactly. This is the
 * single DTO shape used by both the WebSocket stream and its REST
 * fallback, and by both SimulationTelemetryProvider and (once
 * implemented) HardwareTelemetryProvider on the backend — the 3D scene
 * depends on this shape only, never on which provider produced it.
 */

export type TelemetrySource = "SIMULATED" | "HARDWARE";

export type DeviceType = "METER" | "SOLAR_INVERTER" | "BATTERY" | "LOAD_CONTROLLER" | "SENSOR" | "OTHER";

export type DeviceStatus = "ONLINE" | "OFFLINE" | "FAULT" | "DECOMMISSIONED";

export type LoadCategory = "HVAC" | "WATER_HEATER" | "EV_CHARGER" | "LIGHTING" | "APPLIANCE" | "OTHER";

export type LoadControlMode = "MANUAL" | "AUTOMATIC";

export type LoadStatus = "ON" | "OFF" | "UNKNOWN";

export type MicrogridStatus = "ACTIVE" | "INACTIVE" | "MAINTENANCE";

export interface EnergyReading {
  id: string;
  microgrid_id: string;
  recorded_at: string;
  consumption_w: number;
  generation_w: number;
  grid_import_w: number;
  grid_export_w: number;
  available_energy_w: number;
  battery_soc_percent: number | null;
  battery_power_w: number | null;
  source: TelemetrySource;
}

export interface DeviceSnapshotReading {
  device_id: string;
  device_type: DeviceType;
  status: DeviceStatus;
  recorded_at: string;
  power_w: number;
  voltage_v: number;
  current_a: number;
  source: TelemetrySource;
}

export interface LoadSnapshot {
  load_id: string;
  name: string;
  category: LoadCategory;
  priority: number;
  controllable: boolean;
  control_mode: LoadControlMode;
  status: LoadStatus;
}

export interface MicrogridSnapshot {
  microgrid_id: string;
  name: string;
  location: string;
  status: MicrogridStatus;
  server_time: string;
  source: TelemetrySource;
  energy_reading: EnergyReading | null;
  devices: DeviceSnapshotReading[];
  loads: LoadSnapshot[];
  energy_reading_error: string | null;
}

/** The WebSocket wraps a MicrogridSnapshot with a discriminator; errors use a distinct shape. */
export type StreamMessage =
  | ({ type: "snapshot" } & MicrogridSnapshot)
  | { type: "error"; code: string; message: string };
