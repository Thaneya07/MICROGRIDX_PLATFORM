import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionPanel } from "@/components/scene/DecisionPanel";
import type { Decision } from "@/types/decision";
import type { DecisionState } from "@/hooks/useDecision";

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
  recommended_battery_action: "DISCHARGE",
  recommended_battery_power_w: 250,
  load_recommendations: [
    { load_id: "l-1", load_name: "EV Charger", action: "DEFER", reason: "Low priority.", priority: 1 },
    { load_id: "l-2", load_name: "Fridge", action: "MAINTAIN", reason: "No change.", priority: 10 },
  ],
  expected_grid_import_wh: 200,
  expected_grid_export_wh: 0,
  expected_renewable_utilization_pct: 80,
  expected_peak_w: 300,
  constraints_checked: [],
  constraints_satisfied: true,
  explanation: "Battery discharge recommended at 250 W.",
  recommendation_reason: "Discharging recommended.",
  fallback_used: false,
  fallback_reason: null,
  provenance: {},
  approval_status: "PENDING",
  approved_at: null,
  safety_note: "This is a decision-support recommendation only. MicroGridX does not automatically actuate physical hardware.",
};

function makeState(overrides: Partial<DecisionState> = {}): DecisionState {
  return {
    status: "success",
    decision: SAMPLE_DECISION,
    errorMessage: null,
    runOptimization: vi.fn(),
    approve: vi.fn(),
    ...overrides,
  };
}

describe("DecisionPanel", () => {
  it("always renders a RECOMMENDATION badge, never implying a live measurement", () => {
    render(<DecisionPanel state={makeState()} />);
    expect(screen.getByText("RECOMMENDATION")).toBeInTheDocument();
  });

  it("shows the battery action and optimization status", () => {
    render(<DecisionPanel state={makeState()} />);
    expect(screen.getByText("OPTIMAL")).toBeInTheDocument();
    expect(screen.getByText(/DISCHARGE/)).toBeInTheDocument();
  });

  it("shows loading state while fetching", () => {
    render(<DecisionPanel state={makeState({ status: "loading", decision: null })} />);
    expect(screen.getByText(/Loading latest recommendation/)).toBeInTheDocument();
  });

  it("shows optimizing state while running a new optimization", () => {
    render(<DecisionPanel state={makeState({ status: "optimizing" })} />);
    expect(screen.getByText(/Running optimization/)).toBeInTheDocument();
  });

  it("shows unavailable state with a call-to-action when no decision exists", () => {
    const runOptimization = vi.fn();
    render(<DecisionPanel state={makeState({ status: "unavailable", decision: null, runOptimization })} />);
    expect(screen.getByText(/No recommendation yet/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Run optimization now"));
    expect(runOptimization).toHaveBeenCalled();
  });

  it("shows error state with retry", () => {
    const runOptimization = vi.fn();
    render(
      <DecisionPanel
        state={makeState({ status: "error", decision: null, errorMessage: "boom", runOptimization })}
      />
    );
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("shows the FALLBACK badge when fallback_used is true", () => {
    const fallbackDecision: Decision = { ...SAMPLE_DECISION, fallback_used: true, optimization_status: "SAFE_FALLBACK" };
    render(<DecisionPanel state={makeState({ decision: fallbackDecision })} />);
    expect(screen.getByText("FALLBACK")).toBeInTheDocument();
    expect(screen.getByText("SAFE_FALLBACK")).toBeInTheDocument();
  });

  it("shows non-MAINTAIN load recommendations but not MAINTAIN ones", () => {
    render(<DecisionPanel state={makeState()} />);
    expect(screen.getByText("EV Charger")).toBeInTheDocument();
    expect(screen.queryByText("Fridge")).not.toBeInTheDocument();
  });

  it("always displays the backend safety note verbatim", () => {
    render(<DecisionPanel state={makeState()} />);
    expect(screen.getByText(/does not automatically actuate physical hardware/)).toBeInTheDocument();
  });

  it("calls approve(true) and approve(false) from their respective buttons", () => {
    const approve = vi.fn();
    render(<DecisionPanel state={makeState({ approve })} />);
    fireEvent.click(screen.getByText("Approve"));
    expect(approve).toHaveBeenCalledWith(true);
    fireEvent.click(screen.getByText("Reject"));
    expect(approve).toHaveBeenCalledWith(false);
  });

  it("shows approval status badge instead of buttons once approved", () => {
    const approvedDecision: Decision = { ...SAMPLE_DECISION, approval_status: "APPROVED" };
    render(<DecisionPanel state={makeState({ decision: approvedDecision })} />);
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
  });

  it("re-optimize button triggers runOptimization", () => {
    const runOptimization = vi.fn();
    render(<DecisionPanel state={makeState({ runOptimization })} />);
    fireEvent.click(screen.getByText("Re-optimize"));
    expect(runOptimization).toHaveBeenCalled();
  });
});
