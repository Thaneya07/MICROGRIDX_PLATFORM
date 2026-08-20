import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDecision } from "@/hooks/useDecision";
import { apiClient } from "@/services/apiClient";
import type { Decision } from "@/types/decision";

const SAMPLE_DECISION: Decision = {
  id: "d-1",
  microgrid_id: "mg-1",
  created_at: "2026-06-15T12:00:00Z",
  source: "SIMULATED",
  optimization_status: "OPTIMAL",
  horizon_start: "2026-06-15T12:00:00Z",
  horizon_end: "2026-06-15T16:00:00Z",
  interval_minutes: 30,
  objective_value: 100.0,
  recommended_battery_action: "CHARGE",
  recommended_battery_power_w: 500,
  load_recommendations: [],
  expected_grid_import_wh: 200,
  expected_grid_export_wh: 0,
  expected_renewable_utilization_pct: 80,
  expected_peak_w: 300,
  constraints_checked: [],
  constraints_satisfied: true,
  explanation: "Battery charging recommended.",
  recommendation_reason: "Charging recommended.",
  fallback_used: false,
  fallback_reason: null,
  provenance: {},
  approval_status: "PENDING",
  approved_at: null,
  safety_note: "This is a decision-support recommendation only.",
};

describe("useDecision", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stays idle when microgridId is null", () => {
    const { result } = renderHook(() => useDecision(null));
    expect(result.current.status).toBe("idle");
  });

  it("transitions to success with a decision", async () => {
    vi.spyOn(apiClient, "getLatestDecision").mockResolvedValue(SAMPLE_DECISION);
    const { result } = renderHook(() => useDecision("mg-1"));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.decision).toEqual(SAMPLE_DECISION);
  });

  it("treats 'no decision exists' as unavailable, not an error", async () => {
    vi.spyOn(apiClient, "getLatestDecision").mockRejectedValue(
      new Error("No decision exists yet for microgrid mg-1.")
    );
    const { result } = renderHook(() => useDecision("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("unavailable"));
  });

  it("treats other errors as a hard error", async () => {
    vi.spyOn(apiClient, "getLatestDecision").mockRejectedValue(new Error("Network unreachable"));
    const { result } = renderHook(() => useDecision("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("error"));
  });

  it("runOptimization transitions through optimizing to success", async () => {
    vi.spyOn(apiClient, "getLatestDecision").mockRejectedValue(new Error("No decision exists yet."));
    vi.spyOn(apiClient, "optimizeDecision").mockResolvedValue(SAMPLE_DECISION);

    const { result } = renderHook(() => useDecision("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("unavailable"));

    act(() => {
      result.current.runOptimization();
    });
    expect(result.current.status).toBe("optimizing");

    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.decision).toEqual(SAMPLE_DECISION);
  });

  it("approve() updates the decision's approval status", async () => {
    vi.spyOn(apiClient, "getLatestDecision").mockResolvedValue(SAMPLE_DECISION);
    const approved = { ...SAMPLE_DECISION, approval_status: "APPROVED" as const };
    const approveSpy = vi.spyOn(apiClient, "approveDecision").mockResolvedValue(approved);

    const { result } = renderHook(() => useDecision("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("success"));

    act(() => {
      result.current.approve(true);
    });

    await waitFor(() => expect(result.current.decision?.approval_status).toBe("APPROVED"));
    expect(approveSpy).toHaveBeenCalledWith("d-1", true);
  });
});
