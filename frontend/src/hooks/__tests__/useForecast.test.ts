import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useForecast } from "@/hooks/useForecast";
import { apiClient } from "@/services/apiClient";
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
  data_provenance_note: "SIMULATED/DEMO forecast",
};

describe("useForecast", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("stays idle when microgridId is null", () => {
    const { result } = renderHook(() => useForecast(null, "DEMAND"));
    expect(result.current.status).toBe("idle");
  });

  it("transitions to success with forecast data", async () => {
    vi.spyOn(apiClient, "getForecast").mockResolvedValue(SAMPLE_FORECAST);
    const { result } = renderHook(() => useForecast("mg-1", "DEMAND"));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current.status).toBe("success"));
    expect(result.current.forecast).toEqual(SAMPLE_FORECAST);
  });

  it("treats 'no trained model' errors as unavailable, not a hard error", async () => {
    vi.spyOn(apiClient, "getForecast").mockRejectedValue(
      new Error("No trained DEMAND forecasting model exists yet for this microgrid/source.")
    );
    const { result } = renderHook(() => useForecast("mg-1", "DEMAND"));
    await waitFor(() => expect(result.current.status).toBe("unavailable"));
  });

  it("treats other errors as a hard error", async () => {
    vi.spyOn(apiClient, "getForecast").mockRejectedValue(new Error("Network unreachable"));
    const { result } = renderHook(() => useForecast("mg-1", "DEMAND"));
    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.errorMessage).toBe("Network unreachable");
  });

  it("fetches independently per target", async () => {
    const spy = vi.spyOn(apiClient, "getForecast").mockResolvedValue(SAMPLE_FORECAST);
    renderHook(() => useForecast("mg-1", "SOLAR_GENERATION"));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("mg-1", "SOLAR_GENERATION", expect.any(String), expect.any(String), 30));
  });
});
