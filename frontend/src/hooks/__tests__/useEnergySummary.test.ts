import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useEnergySummary } from "@/hooks/useEnergySummary";
import { apiClient } from "@/services/apiClient";
import type { EnergySummaryResponse } from "@/types/analytics";

const SAMPLE_SUMMARY: EnergySummaryResponse = {
  start: "2026-06-14T00:00:00Z",
  end: "2026-06-15T00:00:00Z",
  reading_count: 48,
  total_consumption_wh: 5000,
  total_generation_wh: 2000,
  solar_self_consumption_wh: 1500,
  grid_import_wh: 3500,
  grid_export_wh: 500,
  peak_demand_w: 900,
  average_demand_w: 400,
  load_factor: 0.44,
  renewable_contribution_pct: 30,
  grid_dependency_pct: 70,
  battery_charge_wh: 200,
  battery_discharge_wh: 180,
  battery_throughput_wh: 380,
};

describe("useEnergySummary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stays idle when microgridId is null", () => {
    const { result } = renderHook(() => useEnergySummary(null));
    expect(result.current.status).toBe("idle");
  });

  it("transitions to success with summary data", async () => {
    vi.spyOn(apiClient, "getEnergySummary").mockResolvedValue(SAMPLE_SUMMARY);
    const { result } = renderHook(() => useEnergySummary("mg-1"));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.summary).toEqual(SAMPLE_SUMMARY);
  });

  it("treats insufficient-data errors as unavailable, not a hard error", async () => {
    vi.spyOn(apiClient, "getEnergySummary").mockRejectedValue(new Error("Not enough telemetry: INSUFFICIENT_DATA"));
    const { result } = renderHook(() => useEnergySummary("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("unavailable"));
  });

  it("treats other errors as a hard error", async () => {
    vi.spyOn(apiClient, "getEnergySummary").mockRejectedValue(new Error("Network unreachable"));
    const { result } = renderHook(() => useEnergySummary("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("error"));
  });
});
