import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ForecastPanel } from "@/components/scene/ForecastPanel";
import type { ForecastResponse } from "@/types/forecast";

const SAMPLE_FORECAST: ForecastResponse = {
  microgrid_id: "mg-1",
  target: "DEMAND",
  dataset_source: "SIMULATED",
  model_id: "model-1",
  model_trained_at: "2026-06-14T00:00:00Z",
  start: "2026-06-15T00:00:00Z",
  end: "2026-06-15T12:00:00Z",
  interval_minutes: 30,
  points: [{ timestamp: "2026-06-15T00:00:00Z", predicted_w: 300, lower_95_w: 250, upper_95_w: 350 }],
  data_provenance_note: "Trained and evaluated on SIMULATED telemetry only.",
};

describe("ForecastPanel", () => {
  it("always renders a FORECAST badge, distinguishing it from live data", () => {
    render(<ForecastPanel title="Demand" state={{ status: "idle", forecast: null, errorMessage: null }} />);
    expect(screen.getByText("FORECAST")).toBeInTheDocument();
  });

  it("shows a loading state", () => {
    render(<ForecastPanel title="Demand" state={{ status: "loading", forecast: null, errorMessage: null }} />);
    expect(screen.getByText(/Loading forecast/)).toBeInTheDocument();
  });

  it("shows an unavailable state when no model has been trained", () => {
    render(<ForecastPanel title="Demand" state={{ status: "unavailable", forecast: null, errorMessage: null }} />);
    expect(screen.getByText(/No forecast model trained yet/)).toBeInTheDocument();
  });

  it("shows an error state", () => {
    render(
      <ForecastPanel
        title="Demand"
        state={{ status: "error", forecast: null, errorMessage: "Network unreachable" }}
      />
    );
    expect(screen.getByText("Network unreachable")).toBeInTheDocument();
  });

  it("renders forecast points and the provenance note on success", () => {
    render(
      <ForecastPanel title="Demand" state={{ status: "success", forecast: SAMPLE_FORECAST, errorMessage: null }} />
    );
    expect(screen.getByText(/300W/)).toBeInTheDocument();
    expect(screen.getByText(/Trained and evaluated on SIMULATED telemetry only\./)).toBeInTheDocument();
  });
});
