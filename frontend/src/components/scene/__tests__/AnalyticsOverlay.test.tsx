import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnalyticsOverlay } from "@/components/scene/AnalyticsOverlay";
import type { EnergySummaryResponse } from "@/types/analytics";

const SAMPLE: EnergySummaryResponse = {
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

describe("AnalyticsOverlay", () => {
  it("shows loading state", () => {
    render(<AnalyticsOverlay state={{ status: "loading", summary: null, errorMessage: null }} />);
    expect(screen.getByText(/Loading summary/)).toBeInTheDocument();
  });

  it("shows unavailable state for insufficient history", () => {
    render(<AnalyticsOverlay state={{ status: "unavailable", summary: null, errorMessage: null }} />);
    expect(screen.getByText(/Not enough history yet/)).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(<AnalyticsOverlay state={{ status: "error", summary: null, errorMessage: "boom" }} />);
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("renders real metric values on success, never fabricated placeholders", () => {
    render(<AnalyticsOverlay state={{ status: "success", summary: SAMPLE, errorMessage: null }} />);
    expect(screen.getByText("30")).toBeInTheDocument(); // renewable %
    expect(screen.getByText("70")).toBeInTheDocument(); // grid dependency %
    expect(screen.getByText("900")).toBeInTheDocument(); // peak demand
  });
});
