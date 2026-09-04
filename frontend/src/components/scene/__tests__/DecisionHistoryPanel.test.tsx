import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DecisionHistoryPanel } from "@/components/scene/DecisionHistoryPanel";
import type { DecisionHistoryState } from "@/hooks/useDecisionHistory";
import type { Decision } from "@/types/decision";

function makeDecision(overrides: Partial<Decision> = {}): Decision {
  return {
    id: "d-1",
    microgrid_id: "mg-1",
    created_at: "2026-06-15T12:00:00Z",
    source: "SIMULATED",
    optimization_status: "OPTIMAL",
    operating_mode: "ECO_MODE",
    operating_mode_reason: "Battery discharge is recommended.",
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
    ...overrides,
  };
}

function makeState(overrides: Partial<DecisionHistoryState> = {}): DecisionHistoryState {
  return {
    status: "success",
    decisions: [makeDecision()],
    errorMessage: null,
    refresh: vi.fn(),
    ...overrides,
  };
}

describe("DecisionHistoryPanel", () => {
  it("always renders a HISTORY badge", () => {
    render(<DecisionHistoryPanel state={makeState()} />);
    expect(screen.getByText("HISTORY")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<DecisionHistoryPanel state={makeState({ status: "loading", decisions: [] })} />);
    expect(screen.getByText(/Loading decision history/)).toBeInTheDocument();
  });

  it("shows empty state when no decisions exist yet", () => {
    render(<DecisionHistoryPanel state={makeState({ status: "empty", decisions: [] })} />);
    expect(screen.getByText("No decisions yet")).toBeInTheDocument();
  });

  it("shows error state with retry", () => {
    const refresh = vi.fn();
    render(
      <DecisionHistoryPanel
        state={makeState({ status: "error", decisions: [], errorMessage: "boom", refresh })}
      />
    );
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("renders one row per decision with mode, battery action, and approval status", () => {
    render(<DecisionHistoryPanel state={makeState()} />);
    expect(screen.getByText("ECO")).toBeInTheDocument();
    expect(screen.getByText("DISCHARGE")).toBeInTheDocument();
    expect(screen.getByText("PENDING")).toBeInTheDocument();
  });

  it("summarizes load recommendations per row without showing details until expanded", () => {
    render(<DecisionHistoryPanel state={makeState()} />);
    expect(screen.getByText("1 deferred")).toBeInTheDocument();
    expect(screen.queryByText("Battery discharge recommended at 250 W.")).not.toBeInTheDocument();
  });

  it("expands a row on click to reveal the full explanation and load reasons", () => {
    render(<DecisionHistoryPanel state={makeState()} />);
    fireEvent.click(screen.getByText("1 deferred").closest("button")!);
    expect(screen.getByText("Battery discharge recommended at 250 W.")).toBeInTheDocument();
    expect(screen.getByText(/EV Charger/)).toBeInTheDocument();
  });

  it("collapses an expanded row when clicked again", () => {
    render(<DecisionHistoryPanel state={makeState()} />);
    const button = screen.getByText("1 deferred").closest("button")!;
    fireEvent.click(button);
    expect(screen.getByText("Battery discharge recommended at 250 W.")).toBeInTheDocument();
    fireEvent.click(button);
    expect(screen.queryByText("Battery discharge recommended at 250 W.")).not.toBeInTheDocument();
  });

  it("renders multiple decisions distinctly, comparable at a glance", () => {
    const decisions = [
      makeDecision({ id: "d-1", operating_mode: "NORMAL_MODE", recommended_battery_action: "CHARGE" }),
      makeDecision({ id: "d-2", operating_mode: "EMERGENCY_MODE", recommended_battery_action: "IDLE" }),
    ];
    render(<DecisionHistoryPanel state={makeState({ decisions })} />);
    expect(screen.getByText("NORMAL")).toBeInTheDocument();
    expect(screen.getByText("EMERGENCY")).toBeInTheDocument();
    expect(screen.getByText("CHARGE")).toBeInTheDocument();
    expect(screen.getByText("IDLE")).toBeInTheDocument();
  });

  it("shows a no-load-changes summary for decisions with only MAINTAIN recommendations", () => {
    const decision = makeDecision({
      load_recommendations: [
        { load_id: "l-1", load_name: "Fridge", action: "MAINTAIN", reason: "No change.", priority: 10 },
      ],
    });
    render(<DecisionHistoryPanel state={makeState({ decisions: [decision] })} />);
    expect(screen.getByText("No load changes")).toBeInTheDocument();
  });

  it("shows the idle empty state when no microgrid is selected", () => {
    render(<DecisionHistoryPanel state={makeState({ status: "idle", decisions: [] })} />);
    expect(screen.getByText("No microgrid selected")).toBeInTheDocument();
  });
});
