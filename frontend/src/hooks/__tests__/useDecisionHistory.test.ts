import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDecisionHistory } from "@/hooks/useDecisionHistory";
import { apiClient } from "@/services/apiClient";
import type { Decision } from "@/types/decision";

function makeDecision(overrides: Partial<Decision> = {}): Decision {
  return {
    id: "d-1",
    microgrid_id: "mg-1",
    created_at: "2026-06-15T12:00:00Z",
    source: "SIMULATED",
    optimization_status: "OPTIMAL",
    operating_mode: "NORMAL_MODE",
    operating_mode_reason: "Everything is fine.",
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
    ...overrides,
  };
}

describe("useDecisionHistory", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stays idle when microgridId is null", () => {
    const { result } = renderHook(() => useDecisionHistory(null));
    expect(result.current.status).toBe("idle");
  });

  it("transitions to success with a list of decisions", async () => {
    const decisions = [makeDecision({ id: "d-2" }), makeDecision({ id: "d-1" })];
    vi.spyOn(apiClient, "getDecisionHistory").mockResolvedValue(decisions);
    const { result } = renderHook(() => useDecisionHistory("mg-1"));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.decisions).toEqual(decisions);
  });

  it("transitions to empty when the list is empty", async () => {
    vi.spyOn(apiClient, "getDecisionHistory").mockResolvedValue([]);
    const { result } = renderHook(() => useDecisionHistory("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("empty"));
  });

  it("surfaces a fetch error", async () => {
    vi.spyOn(apiClient, "getDecisionHistory").mockRejectedValue(new Error("Network unreachable"));
    const { result } = renderHook(() => useDecisionHistory("mg-1"));
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("Network unreachable");
  });

  it("passes the limit through to the API call", async () => {
    const spy = vi.spyOn(apiClient, "getDecisionHistory").mockResolvedValue([]);
    renderHook(() => useDecisionHistory("mg-1", 5));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("mg-1", 5));
  });

  it("re-fetches when refreshSignal changes", async () => {
    const spy = vi.spyOn(apiClient, "getDecisionHistory").mockResolvedValue([]);
    const { rerender } = renderHook(({ signal }) => useDecisionHistory("mg-1", 8, signal), {
      initialProps: { signal: "a" },
    });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

    rerender({ signal: "b" });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
  });

  it("does not re-fetch when refreshSignal stays the same across unrelated re-renders", async () => {
    const spy = vi.spyOn(apiClient, "getDecisionHistory").mockResolvedValue([]);
    const { rerender } = renderHook(({ signal }) => useDecisionHistory("mg-1", 8, signal), {
      initialProps: { signal: "a" },
    });
    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));

    rerender({ signal: "a" });
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
