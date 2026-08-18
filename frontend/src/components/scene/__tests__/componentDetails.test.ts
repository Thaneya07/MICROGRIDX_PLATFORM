import { describe, expect, it } from "vitest";
import {
  buildBatteryDetails,
  buildGridDetails,
  buildLoadControllerDetails,
  buildLoadDetails,
  buildSensorDetails,
  buildSolarDetails,
} from "@/components/scene/componentDetails";
import type { DeviceSnapshotReading, LoadSnapshot, MicrogridSnapshot } from "@/types/telemetry";

function makeSnapshot(overrides: Partial<MicrogridSnapshot> = {}): MicrogridSnapshot {
  return {
    microgrid_id: "mg-1",
    name: "Test Grid",
    location: "Site A",
    status: "ACTIVE",
    server_time: "2026-06-15T12:00:00Z",
    source: "SIMULATED",
    energy_reading: {
      id: "er-1",
      microgrid_id: "mg-1",
      recorded_at: "2026-06-15T12:00:00Z",
      consumption_w: 500,
      generation_w: 300,
      grid_import_w: 200,
      grid_export_w: 0,
      available_energy_w: 300,
      battery_soc_percent: 60,
      battery_power_w: -50,
      source: "SIMULATED",
    },
    devices: [],
    loads: [],
    energy_reading_error: null,
    ...overrides,
  };
}

const DEVICE: DeviceSnapshotReading = {
  device_id: "d-1",
  device_type: "SOLAR_INVERTER",
  status: "ONLINE",
  recorded_at: "2026-06-15T12:00:00Z",
  power_w: 300,
  voltage_v: 231,
  current_a: 1.3,
  source: "SIMULATED",
};

const LOAD: LoadSnapshot = {
  load_id: "l-1",
  name: "Water Pump",
  category: "OTHER",
  priority: 2,
  controllable: true,
  control_mode: "AUTOMATIC",
  status: "ON",
};

describe("componentDetails builders", () => {
  it("buildSolarDetails reports generation and device electricals", () => {
    const details = buildSolarDetails(makeSnapshot(), DEVICE);
    expect(details.kind).toBe("solar");
    expect(details.details.find((d) => d.label === "Generation")?.value).toBe("300 W");
  });

  it("buildBatteryDetails labels charging correctly for negative battery_power_w", () => {
    const details = buildBatteryDetails(makeSnapshot(), DEVICE);
    expect(details.details.find((d) => d.label === "Power flow")?.value).toBe("Charging");
  });

  it("buildBatteryDetails labels discharging correctly for positive battery_power_w", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, battery_power_w: 120 },
    });
    const details = buildBatteryDetails(snapshot, DEVICE);
    expect(details.details.find((d) => d.label === "Power flow")?.value).toBe("Discharging");
  });

  it("buildGridDetails reports importing direction", () => {
    const details = buildGridDetails(makeSnapshot(), DEVICE);
    expect(details.details.find((d) => d.label === "Direction")?.value).toBe("Importing");
  });

  it("buildGridDetails reports exporting direction", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, grid_import_w: 0, grid_export_w: 150 },
    });
    const details = buildGridDetails(snapshot, DEVICE);
    expect(details.details.find((d) => d.label === "Direction")?.value).toBe("Exporting");
  });

  it("buildLoadControllerDetails counts active loads", () => {
    const details = buildLoadControllerDetails([LOAD, { ...LOAD, load_id: "l-2", status: "OFF" }], DEVICE);
    expect(details.details.find((d) => d.label === "Managed loads")?.value).toBe("2");
    expect(details.details.find((d) => d.label === "Active loads")?.value).toBe("1");
  });

  it("buildLoadDetails surfaces the load's own fields", () => {
    const details = buildLoadDetails(LOAD);
    expect(details.title).toBe("Water Pump");
    expect(details.details.find((d) => d.label === "Priority")?.value).toBe("2");
  });

  it("buildSensorDetails includes the explicit source", () => {
    const sensorDevice: DeviceSnapshotReading = { ...DEVICE, device_type: "SENSOR", source: "HARDWARE" };
    const details = buildSensorDetails(sensorDevice);
    expect(details.details.find((d) => d.label === "Source")?.value).toBe("HARDWARE");
  });
});
