import { describe, expect, it } from "vitest";
import {
  devicesByType,
  getBatteryFlowState,
  getConsumptionW,
  getGenerationW,
  getGridFlowState,
  hasLiveData,
  isDeviceOnline,
  isHardware,
  isSimulated,
} from "@/components/scene/sceneMapping";
import type { MicrogridSnapshot } from "@/types/telemetry";

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
      battery_power_w: 0,
      source: "SIMULATED",
    },
    devices: [
      {
        device_id: "d-solar",
        device_type: "SOLAR_INVERTER",
        status: "ONLINE",
        recorded_at: "2026-06-15T12:00:00Z",
        power_w: 300,
        voltage_v: 230,
        current_a: 1.3,
        source: "SIMULATED",
      },
      {
        device_id: "d-battery",
        device_type: "BATTERY",
        status: "OFFLINE",
        recorded_at: "2026-06-15T12:00:00Z",
        power_w: 0,
        voltage_v: 230,
        current_a: 0,
        source: "SIMULATED",
      },
    ],
    loads: [],
    energy_reading_error: null,
    ...overrides,
  };
}

describe("devicesByType / isDeviceOnline", () => {
  it("filters devices by type", () => {
    const snapshot = makeSnapshot();
    expect(devicesByType(snapshot, "SOLAR_INVERTER")).toHaveLength(1);
    expect(devicesByType(snapshot, "METER")).toHaveLength(0);
  });

  it("reports online status correctly, including for a missing device", () => {
    const snapshot = makeSnapshot();
    expect(isDeviceOnline(devicesByType(snapshot, "SOLAR_INVERTER")[0])).toBe(true);
    expect(isDeviceOnline(devicesByType(snapshot, "BATTERY")[0])).toBe(false);
    expect(isDeviceOnline(devicesByType(snapshot, "METER")[0])).toBe(false);
  });
});

describe("getBatteryFlowState", () => {
  it("reports discharging for positive battery_power_w", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, battery_power_w: 150 },
    });
    expect(getBatteryFlowState(snapshot)).toBe("discharging");
  });

  it("reports charging for negative battery_power_w", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, battery_power_w: -80 },
    });
    expect(getBatteryFlowState(snapshot)).toBe("charging");
  });

  it("reports idle for near-zero battery_power_w", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, battery_power_w: 0.2 },
    });
    expect(getBatteryFlowState(snapshot)).toBe("idle");
  });

  it("reports unknown when battery_power_w is null", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, battery_power_w: null },
    });
    expect(getBatteryFlowState(snapshot)).toBe("unknown");
  });

  it("reports unknown when there is no energy reading at all", () => {
    const snapshot = makeSnapshot({ energy_reading: null });
    expect(getBatteryFlowState(snapshot)).toBe("unknown");
  });
});

describe("getGridFlowState", () => {
  it("reports importing when grid_import_w dominates", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, grid_import_w: 300, grid_export_w: 0 },
    });
    expect(getGridFlowState(snapshot)).toBe("importing");
  });

  it("reports exporting when grid_export_w dominates", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, grid_import_w: 0, grid_export_w: 250 },
    });
    expect(getGridFlowState(snapshot)).toBe("exporting");
  });

  it("reports balanced when both are ~zero", () => {
    const snapshot = makeSnapshot({
      energy_reading: { ...makeSnapshot().energy_reading!, grid_import_w: 0, grid_export_w: 0 },
    });
    expect(getGridFlowState(snapshot)).toBe("balanced");
  });

  it("reports unknown when there is no energy reading", () => {
    const snapshot = makeSnapshot({ energy_reading: null });
    expect(getGridFlowState(snapshot)).toBe("unknown");
  });
});

describe("hasLiveData / isSimulated / isHardware", () => {
  it("hasLiveData is false when energy_reading is null", () => {
    expect(hasLiveData(makeSnapshot({ energy_reading: null }))).toBe(false);
    expect(hasLiveData(makeSnapshot())).toBe(true);
  });

  it("hasLiveData is false for a null snapshot", () => {
    expect(hasLiveData(null)).toBe(false);
  });

  it("correctly isolates SIMULATED vs HARDWARE source", () => {
    const simulated = makeSnapshot({ source: "SIMULATED" });
    const hardware = makeSnapshot({ source: "HARDWARE" });
    expect(isSimulated(simulated)).toBe(true);
    expect(isHardware(simulated)).toBe(false);
    expect(isSimulated(hardware)).toBe(false);
    expect(isHardware(hardware)).toBe(true);
  });
});

describe("getGenerationW / getConsumptionW", () => {
  it("reads values from the energy reading", () => {
    const snapshot = makeSnapshot();
    expect(getGenerationW(snapshot)).toBe(300);
    expect(getConsumptionW(snapshot)).toBe(500);
  });

  it("defaults to 0 when there is no energy reading", () => {
    const snapshot = makeSnapshot({ energy_reading: null });
    expect(getGenerationW(snapshot)).toBe(0);
    expect(getConsumptionW(snapshot)).toBe(0);
  });
});
